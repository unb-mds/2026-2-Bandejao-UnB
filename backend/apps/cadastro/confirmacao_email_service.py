"""ConfirmacaoEmailService: link de confirmação de e-mail (RF02, Cadastro N4 4b).

Pense no token como a chave de um cofre que vai pelo correio: a pessoa recebe
a chave (o token em claro, só no e-mail) e o banco guarda apenas o molde dela
(o SHA-256). Quem lê o banco vê o molde, mas não consegue abrir o cofre.

Fluxo:
1. `enviar_link(conta)`: o cadastro (BE-05) e o reenvio chamam. Cria um token
   novo, invalida os anteriores da conta e manda o link do PWA por e-mail.
2. `confirmar(token)`: a página `/confirmar-email` do PWA chama, pela API.
   Token válido ativa a conta; inexistente, expirado ou já usado levanta
   `TokenExpiradoOuInvalidoError` (410).
3. `conta_para_reenvio(...)` + `reenviar(conta)`: a tela de login (matrícula)
   ou a do link expirado (token) pedem um link novo. Só a conta pendente
   recebe e-mail, mas a resposta HTTP é sempre a mesma (RF02.2).
"""

import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.erros import TokenExpiradoOuInvalidoError
from apps.cadastro.models import StatusUsuario, TipoToken, Token, Usuario

logger = logging.getLogger(__name__)

# Anexo A, "Validade do link de confirmação de e-mail": 24 horas. Vale também
# para o prazo da exclusão do cadastro pendente (RF02.3). Fica aqui até a BD-04
# (#90) decidir em qual classe de `config/parametros.py` ele entra.
VALIDADE_DO_LINK = timedelta(hours=24)

ASSUNTO = "Confirme seu e-mail no Bandejão UnB"
CORPO = """Olá, {apelido}!

Para ativar sua conta no Bandejão UnB, abra o link abaixo:

{link}

O link vale por 24 horas e só pode ser usado uma vez. Se ele vencer, peça um
novo na tela de entrar.

Se você não criou uma conta no Bandejão UnB, ignore este e-mail.
"""


def hash_do_token(token: str) -> str:
    """SHA-256 em hexadecimal (64 caracteres), o formato de `Token.token_hash`."""
    return hashlib.sha256(token.encode()).hexdigest()


class ConfirmacaoEmailService:
    def __init__(self):
        self.conta_repository = ContaRepository()

    def enviar_link(self, conta: Usuario) -> None:
        """Gera um link novo (24 h) e manda para o e-mail institucional.

        Os links anteriores da conta deixam de valer. Se o SMTP falhar, a conta
        continua pendente e a pessoa pode pedir o reenvio: o erro vai para o
        log (sem token e sem e-mail) e não sobe para quem chamou.
        """
        token = secrets.token_urlsafe(32)
        agora = timezone.now()
        with transaction.atomic():
            Token.objects.filter(
                usuario=conta,
                tipo=TipoToken.CONFIRMACAO_EMAIL,
                usado_em__isnull=True,
            ).update(usado_em=agora)
            Token.objects.create(
                usuario=conta,
                tipo=TipoToken.CONFIRMACAO_EMAIL,
                token_hash=hash_do_token(token),
                expira_em=agora + VALIDADE_DO_LINK,
            )

        try:
            send_mail(
                ASSUNTO,
                CORPO.format(apelido=conta.apelido, link=self._link_do_pwa(token)),
                # None: usa o DEFAULT_FROM_EMAIL (nao-responda@..., ADR 0012).
                None,
                [conta.email_institucional],
            )
        except Exception as exc:  # noqa: BLE001 - qualquer falha do backend de e-mail
            # Só o id da conta e o nome da exceção: a mensagem de um erro SMTP
            # pode trazer o endereço do destinatário. Sem traceback pelo mesmo
            # motivo (ele mostraria os argumentos).
            logger.error(
                "Falha ao enviar o link de confirmação da conta %s: %s",
                conta.pk,
                type(exc).__name__,
            )

    def confirmar(self, token: str) -> None:
        """Ativa a conta dona do token. Levanta `TokenExpiradoOuInvalidoError`."""
        with transaction.atomic():
            # select_for_update: dois cliques no mesmo link chegam juntos; o
            # segundo espera o primeiro terminar e já encontra `usado_em`.
            registro = (
                Token.objects.select_for_update()
                .select_related("usuario")
                .filter(
                    tipo=TipoToken.CONFIRMACAO_EMAIL,
                    token_hash=hash_do_token(token),
                )
                .first()
            )
            agora = timezone.now()
            if (
                registro is None
                or registro.usado_em is not None
                or registro.expira_em <= agora
                or registro.usuario.status != StatusUsuario.PENDENTE
            ):
                raise TokenExpiradoOuInvalidoError

            registro.usado_em = agora
            registro.save(update_fields=["usado_em"])
            conta = registro.usuario
            conta.email_confirmado = True
            conta.status = StatusUsuario.ATIVO
            conta.save(update_fields=["email_confirmado", "status"])

    def conta_para_reenvio(
        self, matricula_siape: str | None = None, token: str | None = None
    ) -> Usuario | None:
        """Acha a conta pela matrícula/SIAPE ou por um token antigo dela.

        O token pode estar expirado ou usado: aqui ele só identifica a conta
        (a busca é pelo hash, sem olhar a validade). Sem conta, devolve None.
        """
        if matricula_siape:
            return self.conta_repository.buscar_por_identificador(
                matricula_siape.strip()
            )
        if token:
            registro = (
                Token.objects.select_related("usuario")
                .filter(
                    tipo=TipoToken.CONFIRMACAO_EMAIL,
                    token_hash=hash_do_token(token),
                )
                .first()
            )
            return registro.usuario if registro else None
        return None

    def reenviar(self, conta: Usuario | None) -> None:
        """Manda um link novo só se a conta existe e ainda está pendente.

        Quem chama responde igual em todos os casos (RF02.2): assim a rota não
        revela quais contas existem nem quais já foram confirmadas.
        """
        if conta is None:
            return
        if conta.status != StatusUsuario.PENDENTE or conta.email_confirmado:
            return
        self.enviar_link(conta)

    def _link_do_pwa(self, token: str) -> str:
        """O link abre a página `/confirmar-email` do PWA, e não a API.

        A página lê o token da query string e chama
        `POST /api/confirmar-email/{token}/` (#119).
        """
        base = settings.URL_DO_PWA.rstrip("/")
        return f"{base}/confirmar-email?{urlencode({'token': token})}"
