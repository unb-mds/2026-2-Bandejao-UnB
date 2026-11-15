"""LoginService: confere matrícula/SIAPE e senha (RF03.1, RF03.2, Cadastro N4 4c).

Ordem das checagens:
1. formato (RN01): 9 dígitos (matrícula) ou 7 (SIAPE), sem consultar o banco;
2. conta inexistente: mesmo erro da senha errada (RF03.1);
3. bloqueio (RF03.2): bloqueado, a senha nem é conferida;
4. senha, e conta suspensa ou removida (`is_active = False`, ADR 0007): os
   dois casos dão o mesmo erro genérico e contam como tentativa;
5. conta pendente: só quem acertou a senha descobre que falta confirmar o
   e-mail (RF02).

Quem abre a sessão é a `SessaoView`, com o `SessoesDaConta`: assim o service
não depende da requisição HTTP.
"""

from django.contrib.auth.hashers import make_password
from django.db import transaction

from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.erros import (
    ContaNaoConfirmadaError,
    CredenciaisInvalidasError,
    IdentificadorInvalidoError,
    LoginBloqueadoError,
)
from apps.cadastro.models import StatusUsuario, Usuario
from apps.cadastro.tentativa_login_tracker import TentativaLoginTracker
from apps.cadastro.validadores import MatriculaValidator, SiapeValidator

MENSAGEM_IDENTIFICADOR = (
    "Informe a matrícula (9 dígitos) ou o SIAPE (7 dígitos), só com números."
)


class LoginService:
    def __init__(self):
        self.conta_repository = ContaRepository()
        self.tentativa_login_tracker = TentativaLoginTracker()
        self.matricula_validator = MatriculaValidator()
        self.siape_validator = SiapeValidator()

    def autenticar(self, identificador: str, senha: str) -> Usuario:
        """Devolve a conta se ela pode entrar. Senão, levanta um erro de login.

        Levanta `IdentificadorInvalidoError` (422), `CredenciaisInvalidasError`
        (401), `ContaNaoConfirmadaError` (403) ou `LoginBloqueadoError` (429).
        """
        if not (
            self.matricula_validator.validar_formato(identificador)
            or self.siape_validator.validar_formato(identificador)
        ):
            raise IdentificadorInvalidoError(MENSAGEM_IDENTIFICADOR)

        # O erro sai depois do atomic: levantado dentro dele, desfaria a
        # contagem da tentativa que acabou de ser gravada.
        with transaction.atomic():
            conta, erro = self._conferir(identificador, senha)
        if erro is not None:
            raise erro
        return conta

    def _conferir(self, identificador, senha):
        # Trava a conta até o fim da transação: tentativas simultâneas na
        # mesma conta esperam a vez, e nenhuma se perde na contagem.
        conta = self.conta_repository.buscar_por_identificador(
            identificador, travar=True
        )
        if conta is None:
            # Mesmo custo do hash da senha de uma conta que existe: sem isso, a
            # resposta mais rápida revelaria que a conta não existe.
            make_password(senha)
            return None, CredenciaisInvalidasError()

        tracker = self.tentativa_login_tracker
        if tracker.esta_bloqueado(conta):
            return None, LoginBloqueadoError(tracker.segundos_restantes(conta))

        sucesso = conta.check_password(senha) and conta.is_active
        tracker.registrar_tentativa(conta, sucesso=sucesso)
        if not sucesso:
            if tracker.esta_bloqueado(conta):
                # A 5ª falha já responde que bloqueou, como o simulado do #119.
                return None, LoginBloqueadoError(tracker.segundos_restantes(conta))
            return None, CredenciaisInvalidasError()

        if conta.status == StatusUsuario.PENDENTE:
            return None, ContaNaoConfirmadaError()
        return conta, None
