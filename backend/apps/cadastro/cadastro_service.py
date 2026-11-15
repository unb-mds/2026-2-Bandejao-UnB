"""CadastroService: cria a conta pendente (RF01, RN01, RN02, Cadastro N4 4a).

Ordem das checagens do serviço (a mesma do simulado do front, #119):
1. ciência do aviso de privacidade;
2. formato do e-mail e da matrícula (Estudante) ou do SIAPE e do e-mail
   (Professor/Servidor);
3. senha;
4. matrícula/SIAPE ou e-mail já usados (mesma mensagem para os dois);
5. apelido.
A duplicidade vem antes do apelido: senão, o 409 do apelido de um
Professor/Servidor confirmaria que aquele e-mail ainda não tem conta.

Pelo endpoint, o serializer barra antes o que nem tem o formato certo (senha
curta, e-mail malformado, aceite que não é booleano). A ordem acima vale para
o que passa por ele.
"""

import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cadastro.apelido_resolver import MENSAGEM_APELIDO_EM_USO, ApelidoResolver
from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.dados_cadastro import DadosCadastro
from apps.cadastro.erros import (
    CadastroInvalidoError,
    EmailJaCadastradoError,
    IdentificadorJaCadastradoError,
)
from apps.cadastro.identificador_extractor import extractor_para
from apps.cadastro.models import TipoUsuario, Usuario
from apps.cadastro.validadores import (
    EmailInstitucionalValidator,
    MatriculaValidator,
    SenhaValidator,
    SiapeValidator,
)
from apps.gamificacao.pontuacao_service import PontuacaoService
from config.parametros import AvisoPrivacidadeConfig

logger = logging.getLogger(__name__)

MENSAGEM_AVISO = "É preciso aceitar o aviso de privacidade para criar a conta."
MENSAGEM_EMAIL_ESTUDANTE = (
    "Use o e-mail institucional no formato matricula@aluno.unb.br."
)
MENSAGEM_EMAIL_PROFESSOR_SERVIDOR = "Use seu e-mail institucional com domínio @unb.br."
MENSAGEM_MATRICULA_FORMATO = (
    "A matrícula de estudante deve ter exatamente 9 dígitos numéricos."
)
MENSAGEM_MATRICULA_PREFIXO = (
    "Os 3 primeiros dígitos da matrícula não correspondem a um semestre de "
    "ingresso válido."
)
MENSAGEM_MATRICULA_SEQUENCIA = "Matrícula inválida. Confira os dígitos informados."
MENSAGEM_SIAPE = "A matrícula funcional/SIAPE deve ter exatamente 7 dígitos numéricos."
MENSAGEM_SENHA = "A senha deve ter no mínimo 8 caracteres."
MENSAGEM_DADOS = "Confira os dados informados."


class CadastroService:
    def __init__(self, hoje: date | None = None):
        self.matricula_validator = MatriculaValidator(hoje=hoje)
        self.siape_validator = SiapeValidator()
        self.email_validator = EmailInstitucionalValidator()
        self.senha_validator = SenhaValidator()
        self.conta_repository = ContaRepository()
        self.apelido_resolver = ApelidoResolver(self.conta_repository)
        self.pontuacao_service = PontuacaoService()
        self.validacoes_por_tipo = {
            TipoUsuario.ESTUDANTE: self._validar_estudante,
            TipoUsuario.PROFESSOR_SERVIDOR: self._validar_professor_servidor,
        }

    def registrar(self, tipo_usuario: TipoUsuario, dados: DadosCadastro) -> Usuario:
        """Cria a conta `pendente` e os contadores dela, na mesma transação.

        Levanta `CadastroInvalidoError` (422) ou `ApelidoIndisponivelError` (409).
        """
        if dados.aceite_privacidade is not True:
            raise CadastroInvalidoError(MENSAGEM_AVISO)

        validar = self.validacoes_por_tipo.get(tipo_usuario)
        if validar is None:
            raise ValueError(f"Tipo de usuário sem regra de cadastro: {tipo_usuario!r}")
        email = dados.email_institucional.strip()
        extraido = extractor_para(tipo_usuario).extrair(dados)
        validar(email, extraido.identificador)

        if not self.senha_validator.validar(dados.senha):
            raise CadastroInvalidoError(MENSAGEM_SENHA)

        if self.conta_repository.existe_matricula_ou_siape(extraido.identificador):
            raise IdentificadorJaCadastradoError
        if self.conta_repository.existe_email(email):
            raise EmailJaCadastradoError

        # Sem apelido sugerido (Estudante) ou com um apelido digitado, vale o
        # digitado. Senão, o apelido sai do e-mail (Professor/Servidor).
        apelido_digitado = dados.apelido.strip()
        apelido_extraido = (
            extraido.apelido_sugerido is not None and not apelido_digitado
        )
        if apelido_extraido:
            apelido = self.apelido_resolver.resolver_extraido(extraido.apelido_sugerido)
        else:
            apelido = self.apelido_resolver.resolver_manual(apelido_digitado)

        try:
            with transaction.atomic():
                conta = get_user_model().objects.create_user(
                    matricula_siape=extraido.identificador,
                    password=dados.senha,
                    tipo_usuario=tipo_usuario,
                    apelido=apelido,
                    email_institucional=email,
                    aceite_privacidade_em=timezone.now(),
                    versao_aviso_aceita=AvisoPrivacidadeConfig.versao_atual,
                )
                self.pontuacao_service.inicializar_conta(conta)
        except IntegrityError as exc:
            self._classificar_corrida(
                exc,
                tipo_usuario,
                extraido.identificador,
                email,
                apelido,
                apelido_extraido,
            )
            raise
        except ValidationError as exc:
            # Sobra do full_clean do model, que o serializer deveria ter barrado.
            logger.warning(
                "Cadastro recusado pelo full_clean do model: %s",
                sorted(exc.message_dict),
            )
            raise CadastroInvalidoError(MENSAGEM_DADOS) from exc
        return conta

    def _classificar_corrida(
        self, exc, tipo_usuario, identificador, email, apelido, apelido_extraido
    ) -> None:
        """Outro cadastro igual entrou entre a checagem e o INSERT.

        Quem decide é o UNIQUE do banco. A duplicidade é conferida primeiro: no
        duplo clique, o apelido "ocupado" é o da própria pessoa. Um
        IntegrityError que não é nenhum desses casos volta para quem chamou e
        vira 500, com rastro no log.
        """
        # Só o nome da exceção: no MySQL, a mensagem traz o valor repetido.
        logger.warning("Corrida no cadastro (%s): %s", tipo_usuario, type(exc).__name__)
        repositorio = self.conta_repository
        if repositorio.existe_matricula_ou_siape(
            identificador
        ) or repositorio.existe_email(email):
            raise IdentificadorJaCadastradoError from exc
        if not self.apelido_resolver.validar_disponibilidade(apelido):
            if apelido_extraido:
                raise self.apelido_resolver.indisponivel(apelido) from exc
            raise CadastroInvalidoError(MENSAGEM_APELIDO_EM_USO) from exc

    def _validar_estudante(self, email: str, matricula: str) -> None:
        if not self.email_validator.validar_formato_estudante(email):
            raise CadastroInvalidoError(MENSAGEM_EMAIL_ESTUDANTE)
        if not self.matricula_validator.validar_formato(matricula):
            raise CadastroInvalidoError(MENSAGEM_MATRICULA_FORMATO)
        if not self.matricula_validator.validar_prefixo_ano_semestre(matricula):
            raise CadastroInvalidoError(MENSAGEM_MATRICULA_PREFIXO)
        if not self.matricula_validator.validar_sequencia_digitos(matricula):
            raise CadastroInvalidoError(MENSAGEM_MATRICULA_SEQUENCIA)

    def _validar_professor_servidor(self, email: str, siape: str) -> None:
        if not self.siape_validator.validar_formato(siape):
            raise CadastroInvalidoError(MENSAGEM_SIAPE)
        if not self.email_validator.validar_formato_professor_servidor(email):
            raise CadastroInvalidoError(MENSAGEM_EMAIL_PROFESSOR_SERVIDOR)
