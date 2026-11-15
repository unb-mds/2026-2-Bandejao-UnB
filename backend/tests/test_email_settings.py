"""Envio de e-mail (ADR 0012, BE-06).

No Django 6.1, a configuração é o MAILERS; as antigas EMAIL_BACKEND,
EMAIL_HOST etc. estão obsoletas. O MAILERS de antes mandava tudo para o
console, inclusive em produção. Agora o backend depende do DEBUG e do .env.
"""

CONSOLE = "django.core.mail.backends.console.EmailBackend"
SMTP = "django.core.mail.backends.smtp.EmailBackend"
OBSOLETAS = (
    "EMAIL_BACKEND",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_USE_TLS",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_TIMEOUT",
)


def mailer(modulo):
    return modulo.MAILERS["default"]


def test_nenhuma_configuracao_de_email_obsoleta(carregar_settings):
    """O Django 6.1 recusa as EMAIL_* antigas quando há MAILERS."""
    modulo = carregar_settings(DEBUG="False")

    assert not [nome for nome in OBSOLETAS if hasattr(modulo, nome)]


def test_em_desenvolvimento_o_email_vai_para_o_terminal(carregar_settings):
    padrao = mailer(carregar_settings(DEBUG="True"))

    assert padrao["BACKEND"] == CONSOLE
    assert padrao["OPTIONS"] == {}


def test_em_producao_o_padrao_e_o_smtp_do_brevo(carregar_settings):
    modulo = carregar_settings(DEBUG="False")
    padrao = mailer(modulo)

    assert padrao["BACKEND"] == SMTP
    assert padrao["OPTIONS"]["port"] == 587
    assert padrao["OPTIONS"]["use_tls"] is True
    assert padrao["OPTIONS"]["timeout"] == 10
    assert modulo.DEFAULT_FROM_EMAIL == "nao-responda@bandejaounb.com.br"


def test_usuario_e_senha_do_smtp_nao_tem_valor_no_codigo(carregar_settings):
    opcoes = mailer(carregar_settings(DEBUG="False"))["OPTIONS"]

    assert opcoes["username"] == ""
    assert opcoes["password"] == ""


def test_o_env_escolhe_o_backend_e_o_servidor(carregar_settings):
    padrao = mailer(
        carregar_settings(
            DEBUG="True",
            EMAIL_BACKEND=SMTP,
            EMAIL_HOST="smtp.exemplo.br",
            EMAIL_PORT="2525",
            EMAIL_HOST_USER="usuario",
            EMAIL_HOST_PASSWORD="segredo",
        )
    )

    assert padrao["BACKEND"] == SMTP
    assert padrao["OPTIONS"]["host"] == "smtp.exemplo.br"
    assert padrao["OPTIONS"]["port"] == 2525
    assert padrao["OPTIONS"]["username"] == "usuario"
    assert padrao["OPTIONS"]["password"] == "segredo"


def test_url_do_pwa_tem_padrao_de_desenvolvimento(carregar_settings):
    assert carregar_settings().URL_DO_PWA == "http://localhost:5173"
    assert (
        carregar_settings(URL_DO_PWA="https://bandejao.exemplo.br").URL_DO_PWA
        == "https://bandejao.exemplo.br"
    )
