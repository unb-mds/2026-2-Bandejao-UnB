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
import smtplib
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.erros import TokenExpiradoOuInvalidoError
from apps.cadastro.limite_de_taxa import LimiteReenvioPorConta
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

O link vale por {horas} horas e só pode ser usado uma vez. Se ele vencer, peça um
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

        A ordem importa, como trocar a fechadura só depois de entregar a chave
        nova: primeiro grava o token novo, depois manda o e-mail e, só se ele
        sair, invalida os links anteriores da conta.

        Se o envio falhar (erro do SMTP ou da rede), o token novo é apagado e
        os anteriores continuam valendo: a pessoa não fica sem link nenhum, e o
        prazo do job (RF02.3) só renova quando um link chega de fato. O erro vai
        para o log (sem token e sem e-mail) e não sobe para quem chamou. Erros
        de banco e de programação sobem normalmente.
        """
        token = secrets.token_urlsafe(32)
        # Monta a mensagem antes do envio: um erro aqui é bug e tem que subir.
        corpo = CORPO.format(
            apelido=conta.apelido,
            link=self._link_do_pwa(token),
            horas=int(VALIDADE_DO_LINK.total_seconds() // 3600),
        )
        agora = timezone.now()
        novo = Token.objects.create(
            usuario=conta,
            tipo=TipoToken.CONFIRMACAO_EMAIL,
            token_hash=hash_do_token(token),
            expira_em=agora + VALIDADE_DO_LINK,
        )

        try:
            send_mail(
                ASSUNTO,
                corpo,
                # None: usa o DEFAULT_FROM_EMAIL (nao-responda@..., ADR 0012).
                None,
                [conta.email_institucional],
            )
        except (smtplib.SMTPException, OSError) as exc:
            # OSError cobre a rede: conexão recusada, timeout, erro de TLS.
            novo.delete()
            self._registrar_falha_no_envio(conta, exc)
            return

        # Só os links mais antigos que o novo (pk menor): se dois reenvios
        # correrem juntos, o mais recente sobrevive, e não os dois morrem.
        Token.objects.filter(
            usuario=conta,
            tipo=TipoToken.CONFIRMACAO_EMAIL,
            usado_em__isnull=True,
            pk__lt=novo.pk,
        ).update(usado_em=agora)

    def _registrar_falha_no_envio(self, conta: Usuario, exc: Exception) -> None:
        """Log da falha sem dados pessoais.

        Só o id da conta, o nome da exceção e o código SMTP (421, 550...), que
        não carrega endereço. A mensagem da exceção fica de fora porque pode
        trazer o destinatário (`SMTPRecipientsRefused` guarda o endereço), e o
        traceback também, porque mostraria os argumentos.
        """
        codigo = getattr(exc, "smtp_code", None)
        logger.error(
            "Falha ao enviar o link de confirmação da conta %s: %s%s",
            conta.pk,
            type(exc).__name__,
            f" (código SMTP {codigo})" if codigo is not None else "",
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

        A conta que passou do limite de reenvios (`LimiteDeTaxaConfig`, #123)
        também não recebe e-mail, e a resposta continua a mesma: um 429 aqui
        revelaria que a conta existe. O primeiro link, do cadastro, não passa
        por este limite (sai pelo `enviar_link` direto).
        """
        if conta is None:
            return
        if conta.status != StatusUsuario.PENDENTE or conta.email_confirmado:
            return
        if not LimiteReenvioPorConta().permite(conta):
            return
        self.enviar_link(conta)

    def _link_do_pwa(self, token: str) -> str:
        """O link abre a página `/confirmar-email` do PWA, e não a API.

        A página lê o token da query string e chama
        `POST /api/confirmar-email/{token}/` (#119).
        """
        base = settings.URL_DO_PWA.rstrip("/")
        return f"{base}/confirmar-email?{urlencode({'token': token})}"
