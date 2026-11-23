"""Configuração de produção do backend (BE-10, #137)."""

import logging
import os
import shlex
import zoneinfo
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from django.conf import settings as settings_do_projeto
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from rest_framework.test import APIClient

from config.logs import MascaraTokenDoPath

BACKEND = Path(__file__).resolve().parents[1]
WORKFLOW_DO_BACKEND = BACKEND.parent / ".github" / "workflows" / "backend-ci.yml"

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


# Configurações que o check --deploy confere e que dependem do DEBUG. Elas são
# calculadas quando o settings.py é importado: com DJANGO_DEBUG=True no .env
# local, a suíte inteira as herdaria em modo de desenvolvimento.
PREFIXOS_DE_SEGURANCA = ("SECURE_", "SESSION_COOKIE_", "CSRF_COOKIE_")


def test_check_deploy_passa_sem_avisos(settings, carregar_settings):
    """Com os valores de produção (sem DEBUG e sem o .env local), zero aviso."""
    producao = carregar_settings()
    for nome in dir(producao):
        if nome.startswith(PREFIXOS_DE_SEGURANCA):
            setattr(settings, nome, getattr(producao, nome))
    settings.SILENCED_SYSTEM_CHECKS = getattr(producao, "SILENCED_SYSTEM_CHECKS", [])
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


def test_hsts_negativo_derruba_a_subida(carregar_settings):
    """max-age negativo desligaria o HSTS em silêncio, sem o aviso W004."""
    with pytest.raises(ImproperlyConfigured, match="SECURE_HSTS_SECONDS"):
        carregar_settings(SECURE_HSTS_SECONDS="-1")


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


@pytest.mark.django_db
def test_hsts_atras_do_caddy(settings, carregar_settings):
    """Em produção o HTTPS termina no Caddy, que avisa pelo X-Forwarded-Proto.

    Usa o SECURE_PROXY_SSL_HEADER e o HSTS de produção: se o
    ATRAS_DE_PROXY_HTTPS deixar de valer sem DEBUG, o HSTS sumiria do site.
    """
    producao = carregar_settings()
    settings.SECURE_PROXY_SSL_HEADER = producao.SECURE_PROXY_SSL_HEADER
    settings.SECURE_HSTS_SECONDS = producao.SECURE_HSTS_SECONDS
    resposta = APIClient().get("/api/campi/", HTTP_X_FORWARDED_PROTO="https")
    assert resposta.status_code == 200
    assert resposta["Strict-Transport-Security"] == "max-age=3600"


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


@pytest.mark.parametrize(
    "linha",
    [
        "POST /api/confirmar-email/SEGREDO/ HTTP/1.1",
        "POST /api/confirmar-email/SEGREDO HTTP/1.1",
        "POST /api/confirmar-email/SEGREDO?x=1 HTTP/1.1",
        "POST /api/confirmar-email/?token=SEGREDO HTTP/1.1",
        "POST //api//confirmar-email/SEGREDO/ HTTP/1.1",
        "POST /API/Confirmar-Email/SEGREDO/ HTTP/1.1",
    ],
)
def test_mascara_tira_o_token_do_path(linha):
    registro = logging.LogRecord("teste", logging.INFO, __file__, 0, linha, None, None)
    MascaraTokenDoPath().filter(registro)
    assert "SEGREDO" not in registro.getMessage()
    assert "***" in registro.getMessage()


# --- Log do Gunicorn (entrypoint.sh) -----------------------------------------
# O gunicorn só existe na imagem e no job testes-mysql do CI. Fora dele, os
# testes abaixo são ignorados; no CI, o EXIGIR_GUNICORN=1 faz a falta do
# gunicorn ser erro, e não um pulo silencioso.

TOKEN = "TOKEN-SECRETO-123"
EMAIL = "fulano@aluno.unb.br"


@pytest.fixture
def gunicorn():
    if os.environ.get("EXIGIR_GUNICORN") == "1":
        import gunicorn as modulo

        return modulo
    return pytest.importorskip("gunicorn")


def argumentos_do_gunicorn():
    """Argumentos do `exec gunicorn` do entrypoint.sh, como o shell os passa.

    Lê só a linha do exec e as continuações (`\\`): comentários e uma linha
    comentada não contam.
    """
    linhas = (BACKEND / "entrypoint.sh").read_text().splitlines()
    inicio = next(
        i for i, linha in enumerate(linhas) if linha.startswith("exec gunicorn")
    )
    comando = ""
    for linha in linhas[inicio:]:
        comando += linha.rstrip().removesuffix("\\") + " "
        if not linha.rstrip().endswith("\\"):
            break
    return shlex.split(comando)[2:]  # sem o "exec gunicorn"


@pytest.fixture
def log_do_entrypoint(gunicorn):
    """O logger que o Gunicorn monta com a linha do entrypoint.sh.

    Um handler extra guarda as linhas gravadas; no fim, os handlers e filtros
    postos nos loggers globais do Gunicorn são tirados.
    """
    from gunicorn.config import Config

    cfg = Config()
    opcoes = cfg.parser().parse_args(argumentos_do_gunicorn())
    for nome, valor in vars(opcoes).items():
        if valor is not None and nome in cfg.settings:
            cfg.set(nome.lower(), valor)

    log = cfg.logger_class(cfg)
    linhas = []
    guarda = logging.Handler()
    guarda.emit = lambda registro: linhas.append(registro.getMessage())
    for logger in (log.access_log, log.error_log):
        logger.addHandler(guarda)
    yield SimpleNamespace(log=log, cfg=cfg, linhas=linhas)
    for logger in (log.access_log, log.error_log):
        logger.handlers.clear()
        logger.filters.clear()


def requisicao_de_confirmacao():
    """POST da página /confirmar-email do PWA, recusado com 403.

    O Referer vem com o token (link do e-mail) e o e-mail (página aberta depois
    do cadastro), os dois modos da página.
    """
    referer = f"https://bandejaounb.com.br/confirmar-email?token={TOKEN}&email={EMAIL}"
    environ = {
        "REMOTE_ADDR": "172.18.0.4",
        "REQUEST_METHOD": "POST",
        "RAW_URI": f"/api/confirmar-email/{TOKEN}/",
        "PATH_INFO": f"/api/confirmar-email/{TOKEN}/",
        "QUERY_STRING": "",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_REFERER": referer,
        "HTTP_USER_AGENT": "navegador-de-teste",
    }
    requisicao = SimpleNamespace(
        headers=[("REFERER", referer), ("USER-AGENT", "navegador-de-teste")]
    )
    resposta = SimpleNamespace(status="403 Forbidden", sent=126, headers=[])
    return resposta, requisicao, environ


def test_entrypoint_usa_o_logger_sem_token(log_do_entrypoint):
    from config.log_gunicorn import LogDeAcessoSemToken

    assert isinstance(log_do_entrypoint.log, LogDeAcessoSemToken)
    assert log_do_entrypoint.cfg.accesslog == "-"


def test_log_de_acesso_sem_token_e_sem_referer(log_do_entrypoint):
    """Caminho real: Logger.access() com o --access-logformat do entrypoint.sh."""
    resposta, requisicao, environ = requisicao_de_confirmacao()
    log_do_entrypoint.log.access(resposta, requisicao, environ, timedelta(seconds=0))

    (linha,) = log_do_entrypoint.linhas
    assert '"POST /api/confirmar-email/***/ HTTP/1.1" 403 126' in linha
    assert "navegador-de-teste" in linha
    assert TOKEN not in linha
    assert EMAIL not in linha


def test_log_de_erro_do_gunicorn_sem_token(log_do_entrypoint):
    """O worker grava "Error handling request <método> <uri>" no gunicorn.error
    quando uma exceção escapa do WSGI."""
    log_do_entrypoint.log.error(
        "Error handling request %s %s", "POST", f"/api/confirmar-email/{TOKEN}/"
    )
    (linha,) = log_do_entrypoint.linhas
    assert TOKEN not in linha
    assert "/api/confirmar-email/***/" in linha


def test_reload_nao_duplica_o_filtro(log_do_entrypoint):
    """O SIGHUP roda o setup() de novo no mesmo logger."""
    log = log_do_entrypoint.log
    log.setup(log_do_entrypoint.cfg)
    for logger in (log.access_log, log.error_log):
        mascaras = [f for f in logger.filters if isinstance(f, MascaraTokenDoPath)]
        assert len(mascaras) == 1


# --- CI --------------------------------------------------------------------


def job_testes_mysql():
    return yaml.safe_load(WORKFLOW_DO_BACKEND.read_text())["jobs"]["testes-mysql"]


def test_ci_exige_o_gunicorn_no_testes_mysql():
    assert str(job_testes_mysql()["env"]["EXIGIR_GUNICORN"]) == "1"


def test_ci_falha_com_aviso_do_check_deploy():
    """Um aviso novo de segurança falha o CI, em vez de ficar só no log."""
    (passo,) = [
        p for p in job_testes_mysql()["steps"] if "check --deploy" in p.get("run", "")
    ]
    assert "--fail-level WARNING" in passo["run"]
    assert len(passo["env"]["DJANGO_SECRET_KEY"]) >= 50
