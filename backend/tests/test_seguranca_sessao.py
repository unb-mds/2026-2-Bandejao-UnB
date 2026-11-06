"""Sessão por cookie e CSRF por cabeçalho (ADR 0007)."""

from django.conf import settings


def test_cookie_de_sessao_e_httponly():
    assert settings.SESSION_COOKIE_HTTPONLY is True


def test_cookie_de_sessao_e_samesite_lax():
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"


def test_cookie_csrf_legivel_pelo_pwa():
    # O apiClient lê o cookie csrftoken e manda o valor no cabeçalho.
    assert settings.CSRF_COOKIE_HTTPONLY is False
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"


def test_csrf_vem_pelo_cabecalho_x_csrftoken():
    assert settings.CSRF_HEADER_NAME == "HTTP_X_CSRFTOKEN"


def test_sessao_de_14_dias_renovada_a_cada_uso():
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_api_autentica_so_por_sessao():
    autenticacao = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    assert autenticacao == ["rest_framework.authentication.SessionAuthentication"]


def test_api_responde_so_json():
    renderizadores = settings.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"]
    assert renderizadores == ["rest_framework.renderers.JSONRenderer"]
