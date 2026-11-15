"""Envio de e-mail (ADR 0012, BE-06).

No Django 6.1, a configuração é o MAILERS; as antigas EMAIL_BACKEND,
EMAIL_HOST etc. estão obsoletas. O MAILERS de antes mandava tudo para o
console, inclusive em produção. Agora o backend depende do DEBUG e do .env.

Em produção (sem DEBUG), o endereço do PWA e o servidor SMTP não têm valor
padrão, como a SECRET_KEY: esquecer a variável no deploy tem que parar o
servidor na subida, e não mandar e-mails com link para localhost.
"""

import pytest
from decouple import UndefinedValueError

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


# O mínimo para o settings carregar em produção com o SMTP.
PRODUCAO = {
    "DEBUG": "False",
    "URL_DO_PWA": "https://bandejao.exemplo.br",
    "EMAIL_HOST": "smtp.exemplo.br",
    "EMAIL_HOST_USER": "usuario",
    "EMAIL_HOST_PASSWORD": "segredo",
}


def mailer(modulo):
    return modulo.MAILERS["default"]


def sem(*nomes):
    """O ambiente de produção sem as variáveis indicadas (None as tira)."""
    return {**PRODUCAO, **dict.fromkeys(nomes)}


def test_nenhuma_configuracao_de_email_obsoleta(carregar_settings):
    """O Django 6.1 recusa as EMAIL_* antigas quando há MAILERS."""
    modulo = carregar_settings(**PRODUCAO)

    assert not [nome for nome in OBSOLETAS if hasattr(modulo, nome)]


def test_em_desenvolvimento_o_email_vai_para_o_terminal(carregar_settings):
    padrao = mailer(carregar_settings(DEBUG="True"))

    assert padrao["BACKEND"] == CONSOLE
    assert padrao["OPTIONS"] == {}


def test_em_producao_o_padrao_e_o_smtp_do_brevo(carregar_settings):
    modulo = carregar_settings(**PRODUCAO)
    padrao = mailer(modulo)

    assert padrao["BACKEND"] == SMTP
    assert padrao["OPTIONS"]["host"] == "smtp.exemplo.br"
    assert padrao["OPTIONS"]["port"] == 587
    assert padrao["OPTIONS"]["use_tls"] is True
    assert padrao["OPTIONS"]["timeout"] == 10
    assert modulo.DEFAULT_FROM_EMAIL == "nao-responda@bandejaounb.com.br"


@pytest.mark.parametrize(
    "faltando", ["EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"]
)
def test_producao_sem_o_smtp_nao_sobe(carregar_settings, faltando):
    with pytest.raises(UndefinedValueError, match=faltando):
        carregar_settings(**sem(faltando))


def test_producao_sem_url_do_pwa_nao_sobe(carregar_settings):
    with pytest.raises(UndefinedValueError, match="URL_DO_PWA"):
        carregar_settings(**sem("URL_DO_PWA"))


def test_producao_com_outro_backend_nao_pede_o_smtp(carregar_settings):
    modulo = carregar_settings(
        EMAIL_BACKEND=CONSOLE,
        **sem("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"),
    )

    assert mailer(modulo)["OPTIONS"] == {}


def test_desenvolvimento_com_smtp_aceita_valores_vazios(carregar_settings):
    """Com DEBUG, o SMTP de verdade é opcional: quem testa preenche o .env."""
    modulo = carregar_settings(
        DEBUG="True",
        EMAIL_BACKEND=SMTP,
        EMAIL_HOST=None,
        EMAIL_HOST_USER=None,
        EMAIL_HOST_PASSWORD=None,
    )
    opcoes = mailer(modulo)["OPTIONS"]

    assert opcoes["host"] == "localhost"
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


def test_url_do_pwa_tem_padrao_so_em_desenvolvimento(carregar_settings):
    dev = carregar_settings(DEBUG="True", URL_DO_PWA=None)
    assert dev.URL_DO_PWA == "http://localhost:5173"
    assert carregar_settings(**PRODUCAO).URL_DO_PWA == "https://bandejao.exemplo.br"


def test_os_logs_do_projeto_aparecem_no_console(carregar_settings):
    """Sem isto, o logger.error do envio sai sem nível nem horário (lastResort) e
    o logger.info do job nunca aparece."""
    modulo = carregar_settings(DEBUG="True")
    apps = modulo.LOGGING["loggers"]["apps"]

    assert apps["handlers"] == ["console"]
    assert apps["level"] == "INFO"
    assert "formatters" in modulo.LOGGING
    assert "asctime" in modulo.LOGGING["formatters"]["padrao"]["format"]
    assert modulo.LOGGING["handlers"]["console"]["formatter"] == "padrao"
