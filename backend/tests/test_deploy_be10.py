"""Configuração de produção do backend (BE-10, #137)."""

import zoneinfo
from pathlib import Path

import pytest
from django.conf import settings as settings_do_projeto
from django.core.management import call_command
from rest_framework.test import APIClient

BACKEND = Path(__file__).resolve().parents[1]

# Longa e variada o bastante para o security.W009 do check --deploy.
CHAVE_DE_PRODUCAO_FALSA = "chave-falsa-de-producao-0123456789-abcdefghijklmnopq"

# Os testes trocam o e-mail pelo backend de memória, que o check --deploy do
# Django 6.1 recusa (mail.E001). Aqui vale o SMTP, como em produção.
SMTP = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {"host": "smtp.teste", "port": 587, "use_tls": True},
    }
}


def test_check_deploy_passa_sem_avisos(settings):
    settings.DEBUG = False
    settings.SECRET_KEY = CHAVE_DE_PRODUCAO_FALSA
    settings.ALLOWED_HOSTS = ["bandejaounb.com.br"]
    settings.MAILERS = SMTP
    call_command("check", "--deploy", "--fail-level", "WARNING")


def test_hsts_padrao_em_producao(carregar_settings):
    modulo = carregar_settings()
    assert modulo.SECURE_HSTS_SECONDS == 3600
    assert modulo.SECURE_HSTS_INCLUDE_SUBDOMAINS is False
    assert modulo.SECURE_HSTS_PRELOAD is False


def test_hsts_desligado_em_desenvolvimento(carregar_settings):
    assert carregar_settings(DJANGO_DEBUG="True").SECURE_HSTS_SECONDS == 0


def test_hsts_pode_vir_do_env(carregar_settings):
    modulo = carregar_settings(SECURE_HSTS_SECONDS="31536000")
    assert modulo.SECURE_HSTS_SECONDS == 31536000


def test_so_tres_avisos_silenciados():
    """Pega quem acrescentar um aviso na lista "para o CI passar"."""
    assert settings_do_projeto.SILENCED_SYSTEM_CHECKS == [
        "security.W005",
        "security.W008",
        "security.W021",
    ]


@pytest.mark.django_db
def test_resposta_por_https_tem_hsts(settings):
    settings.SECURE_HSTS_SECONDS = 3600
    resposta = APIClient().get("/api/campi/", secure=True)
    assert resposta.status_code == 200
    assert resposta["Strict-Transport-Security"] == "max-age=3600"


@pytest.mark.django_db
def test_resposta_por_http_nao_tem_hsts(settings):
    """O Django só manda o HSTS em HTTPS (atrás do Caddy, pelo X-Forwarded-Proto)."""
    settings.SECURE_HSTS_SECONDS = 3600
    resposta = APIClient().get("/api/campi/")
    assert "Strict-Transport-Security" not in resposta


def test_dependencias_de_producao_fixas():
    linhas = [
        linha.strip()
        for linha in (BACKEND / "requirements-prod.txt").read_text().splitlines()
        if linha.strip() and not linha.startswith("#")
    ]
    assert linhas[0] == "-r requirements.txt"
    fixadas = {linha.split("==")[0] for linha in linhas[1:] if "==" in linha}
    assert {"mysqlclient", "gunicorn", "tzdata"} <= fixadas


def test_fuso_do_settings_carrega():
    zoneinfo.ZoneInfo(settings_do_projeto.TIME_ZONE)


def test_log_de_acesso_mascara_o_token():
    """Só roda onde o gunicorn está instalado (job testes-mysql do CI)."""
    pytest.importorskip("gunicorn")
    import logging

    from gunicorn.config import Config

    from config.log_gunicorn import LogDeAcessoSemToken

    log = LogDeAcessoSemToken(Config())
    registro = logging.LogRecord(
        "gunicorn.access",
        logging.INFO,
        __file__,
        0,
        '"%(r)s" %(s)s',
        ({"r": "POST /api/confirmar-email/token-secreto/ HTTP/1.1", "s": "403"},),
        None,
    )
    for filtro in log.access_log.filters:
        filtro.filter(registro)
    assert "token-secreto" not in registro.getMessage()
    assert "/api/confirmar-email/***/" in registro.getMessage()


def test_entrypoint_usa_o_log_sem_token_e_sem_referer():
    """O Referer da página /confirmar-email?token=...&email=... do PWA também
    levaria o token e o e-mail para o log de acesso."""
    entrypoint = (BACKEND / "entrypoint.sh").read_text()
    assert "--logger-class config.log_gunicorn.LogDeAcessoSemToken" in entrypoint
    assert "--access-logformat" in entrypoint
    assert "%(f)s" not in entrypoint
