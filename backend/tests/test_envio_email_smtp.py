"""Envio de e-mail pelo SMTP do Brevo, com o servidor simulado (BD-05, #91).

O teste aplica o MAILERS e o remetente que o settings de produção lê do
ambiente, envia pelo caminho normal do Django (`send_mail`) e troca o
`smtplib.SMTP` por um mock. Assim confere a conversa
com o servidor (porta 587, STARTTLS, login) sem rede e sem credencial real. O
envio de verdade é conferido na VM (docs/deploy/deploy-producao.md).
"""

from unittest import mock

from django.core.mail import send_mail
from django.test import override_settings

PRODUCAO = {
    "DJANGO_DEBUG": "False",
    "EMAIL_HOST": "smtp-relay.brevo.com",
    "EMAIL_PORT": "587",
    "EMAIL_HOST_USER": "login-smtp@brevo",
    "EMAIL_HOST_PASSWORD": "chave-smtp",
    "DEFAULT_FROM_EMAIL": "nao-responda@bandejaounb.com.br",
}


def enviar(modulo, smtp):
    """Envia uma mensagem com o mailer `default` do settings carregado."""
    mailer = modulo.MAILERS["default"]
    assert mailer["BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"

    with (
        override_settings(
            MAILERS=modulo.MAILERS, DEFAULT_FROM_EMAIL=modulo.DEFAULT_FROM_EMAIL
        ),
        mock.patch("django.core.mail.backends.smtp.smtplib.SMTP", smtp),
    ):
        return send_mail(
            "Confirme seu e-mail",
            "Link de confirmação",
            None,  # None: usa o DEFAULT_FROM_EMAIL
            ["202400001@aluno.unb.br"],
        )


def test_envio_usa_o_servidor_a_porta_e_o_tempo_limite(carregar_settings):
    smtp = mock.MagicMock()

    enviados = enviar(carregar_settings(**PRODUCAO), smtp)

    assert enviados == 1
    smtp.assert_called_once()
    assert smtp.call_args.args == ("smtp-relay.brevo.com", 587)
    assert smtp.call_args.kwargs["timeout"] == 10


def test_envio_liga_o_tls_antes_do_login(carregar_settings):
    smtp = mock.MagicMock()
    servidor = smtp.return_value

    enviar(carregar_settings(**PRODUCAO), smtp)

    chamadas = [nome for nome, *_ in servidor.method_calls]
    assert chamadas.index("starttls") < chamadas.index("login")
    servidor.login.assert_called_once_with("login-smtp@brevo", "chave-smtp")


def test_envio_sai_do_remetente_configurado(carregar_settings):
    smtp = mock.MagicMock()
    servidor = smtp.return_value

    enviar(carregar_settings(**PRODUCAO), smtp)

    remetente, destinatarios, _ = servidor.sendmail.call_args.args
    assert remetente == "nao-responda@bandejaounb.com.br"
    assert destinatarios == ["202400001@aluno.unb.br"]
