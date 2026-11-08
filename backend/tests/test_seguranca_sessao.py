"""Sessão por cookie e CSRF por cabeçalho (ADR 0007).

Três camadas, da mais barata para a mais forte:
  1. sentinelas: relêem o settings (pegam alteração acidental do valor);
  2. valores PADRÃO: executam o settings.py do zero, sem .env;
  3. comportamento: fazem requisições de verdade e conferem a resposta
     (CSRF recusado com 403 e cabeçalho Set-Cookie emitido).
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

QUATORZE_DIAS = 14 * 24 * 60 * 60

URLS_DE_TESTE = "tests.urls_csrf"

CONFIGS_DE_COOKIE = [
    "SESSION_COOKIE_HTTPONLY",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_SAMESITE",
    "SESSION_COOKIE_AGE",
    "CSRF_COOKIE_HTTPONLY",
    "CSRF_COOKIE_SECURE",
    "CSRF_COOKIE_SAMESITE",
]


# ---------------------------------------------------------------- 1. sentinelas


def test_cookie_de_sessao_e_httponly(settings):
    assert settings.SESSION_COOKIE_HTTPONLY is True


def test_cookie_de_sessao_e_samesite_lax(settings):
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"


def test_cookie_csrf_legivel_pelo_pwa(settings):
    # O apiClient lê o cookie csrftoken e manda o valor no cabeçalho.
    assert settings.CSRF_COOKIE_HTTPONLY is False
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"


def test_csrf_vem_pelo_cabecalho_x_csrftoken(settings):
    assert settings.CSRF_HEADER_NAME == "HTTP_X_CSRFTOKEN"


def test_sessao_de_14_dias_renovada_a_cada_uso(settings):
    assert settings.SESSION_COOKIE_AGE == QUATORZE_DIAS
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_api_autentica_so_por_sessao(settings):
    # BE-03 (4.1): subclasse da SessionAuthentication que devolve 401, e não 403.
    autenticacao = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    assert autenticacao == ["apps.cadastro.autenticacao.SessaoAutenticacao"]


def test_api_responde_so_json(settings):
    renderizadores = settings.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"]
    assert renderizadores == ["rest_framework.renderers.JSONRenderer"]


def test_csrf_middleware_esta_ativo(settings):
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE


def test_api_exige_login_por_padrao(settings):
    permissoes = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
    assert permissoes == ["rest_framework.permissions.IsAuthenticated"]


# ------------------------------------------------------------ 2. valores padrão


def test_cookies_sao_secure_por_padrao_sem_env(carregar_settings):
    padrao = carregar_settings()
    assert padrao.SESSION_COOKIE_SECURE is True
    assert padrao.CSRF_COOKIE_SECURE is True


def test_secure_acompanha_o_debug_em_desenvolvimento(carregar_settings):
    # Em desenvolvimento (HTTP no runserver) o Secure desliga sozinho, sem o
    # .env precisar repetir isso; em produção DEBUG fica False e vale True.
    dev = carregar_settings(DEBUG="True")
    assert dev.SESSION_COOKIE_SECURE is False
    assert dev.CSRF_COOKIE_SECURE is False


def test_secure_pode_ser_forcado_pelo_env(carregar_settings):
    forcado = carregar_settings(
        DEBUG="True", SESSION_COOKIE_SECURE="True", CSRF_COOKIE_SECURE="True"
    )
    assert forcado.SESSION_COOKIE_SECURE is True
    assert forcado.CSRF_COOKIE_SECURE is True


def test_allowed_hosts_ignora_itens_vazios(carregar_settings):
    padrao = carregar_settings(ALLOWED_HOSTS="a.com, ,b.com,")
    assert padrao.ALLOWED_HOSTS == ["a.com", "b.com"]


# ------------------------------------------------------------- 3. comportamento


@pytest.fixture
def cookies_do_padrao(settings, carregar_settings):
    """Aplica ao Django em execução os valores PADRÃO dos cookies.

    Assim os testes abaixo conferem o Set-Cookie que o Django realmente emite
    com a configuração de produção, sem depender do .env de quem roda.
    """
    padrao = carregar_settings()
    for nome in CONFIGS_DE_COOKIE:
        setattr(settings, nome, getattr(padrao, nome))


@pytest.fixture
def usuario(db):
    return get_user_model().objects.create_user(
        matricula_siape="202400001",
        tipo_usuario="estudante",
        apelido="cris",
        email_institucional="202400001@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )


@pytest.fixture
def cliente_logado(usuario):
    """Cliente que EXIGE CSRF (como um navegador) e já tem sessão."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(usuario)
    return cliente


@pytest.mark.urls(URLS_DE_TESTE)
def test_escrita_sem_csrf_e_recusada(cliente_logado):
    resposta = cliente_logado.post("/teste/escrita/", {}, format="json")
    assert resposta.status_code == 403


@pytest.mark.urls(URLS_DE_TESTE)
def test_escrita_com_csrf_errado_e_recusada(cliente_logado):
    resposta = cliente_logado.post(
        "/teste/escrita/", {}, format="json", HTTP_X_CSRFTOKEN="token-invalido"
    )
    assert resposta.status_code == 403


@pytest.mark.urls(URLS_DE_TESTE)
def test_escrita_com_csrf_valido_e_aceita(cliente_logado):
    # O PWA faz o mesmo: lê o cookie csrftoken e devolve no cabeçalho.
    cliente_logado.get("/teste/escrita/")
    token = cliente_logado.cookies["csrftoken"].value

    resposta = cliente_logado.post(
        "/teste/escrita/", {}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert resposta.status_code == 200


@pytest.mark.urls(URLS_DE_TESTE)
def test_middleware_csrf_recusa_escrita_de_view_django_sem_token():
    # Camada do middleware (a do DRF é a de cima). Sem o CsrfViewMiddleware
    # no settings esta escrita passaria com 200.
    cliente = Client(enforce_csrf_checks=True)
    resposta = cliente.post("/teste/escrita-django/", {})
    assert resposta.status_code == 403


@pytest.mark.urls(URLS_DE_TESTE)
def test_view_sem_permission_classes_nega_anonimo():
    # Esquecer permission_classes não pode deixar a view pública.
    # BE-03 (4.1): sem sessão o backend responde 401 com `nao_autenticado`.
    resposta = APIClient().get("/teste/sem-permissao/")
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


@pytest.mark.urls(URLS_DE_TESTE)
def test_view_sem_permission_classes_aceita_logado(cliente_logado):
    resposta = cliente_logado.get("/teste/sem-permissao/")
    assert resposta.status_code == 200


def _login(usuario):
    cliente = APIClient()
    resposta = cliente.post(
        "/teste/login/",
        {"username": usuario.get_username(), "password": "senha-forte-123"},
        format="json",
    )
    assert resposta.status_code == 200
    return resposta


@pytest.mark.urls(URLS_DE_TESTE)
def test_cookie_de_sessao_emitido_tem_as_flags_da_adr(cookies_do_padrao, usuario):
    cookie = _login(usuario).cookies["sessionid"]

    assert cookie["httponly"]
    assert cookie["secure"]
    assert cookie["samesite"] == "Lax"
    assert int(cookie["max-age"]) == QUATORZE_DIAS


@pytest.mark.urls(URLS_DE_TESTE)
def test_cookie_csrf_emitido_e_legivel_pelo_pwa(cookies_do_padrao, usuario):
    cookie = _login(usuario).cookies["csrftoken"]

    assert not cookie["httponly"]  # o PWA precisa ler para mandar no cabeçalho
    assert cookie["secure"]
    assert cookie["samesite"] == "Lax"


@pytest.mark.urls(URLS_DE_TESTE)
def test_sessao_e_renovada_a_cada_uso(cookies_do_padrao, cliente_logado):
    # SESSION_SAVE_EVERY_REQUEST: toda resposta reemite o cookie por 14 dias.
    cookie = cliente_logado.get("/teste/sem-permissao/").cookies["sessionid"]

    assert int(cookie["max-age"]) == QUATORZE_DIAS
