"""CSRF nas rotas reais do contrato (BE-03, guia 4.1, #112).

Quem tem sessão e escreve sem o token CSRF recebe 403 `csrf_invalido`.
Quem não tem sessão recebe 401 nas rotas logadas. Os dois nunca se confundem:
um 403 de CSRF não pode deslogar o usuário no front, e um 401 não pode
parecer aviso de privacidade pendente.

As escritas públicas (cadastro, login, confirmação e reenvio) também cobram
o CSRF, mesmo sem sessão: sem isso, um site de terceiros conseguiria logar a
vítima na conta do atacante (login CSRF). O PWA pega o cookie `csrftoken`
antes em `GET /api/csrf/`.
"""

import logging

import pytest
from rest_framework.test import APIClient

from tests.rotas_do_contrato import ESCRITAS_LOGADAS, ESCRITAS_PUBLICAS

ROTA_DO_COOKIE = "/api/csrf/"


@pytest.fixture
def cliente_com_sessao(usuario):
    """Cliente que EXIGE CSRF (como um navegador) e já tem sessão."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(usuario)
    return cliente


@pytest.fixture
def cliente_com_token():
    """Cliente sem sessão que já pegou o cookie e manda o token no cabeçalho."""
    cliente = APIClient(enforce_csrf_checks=True)
    resposta = cliente.get(ROTA_DO_COOKIE)
    cliente.credentials(HTTP_X_CSRFTOKEN=resposta.cookies["csrftoken"].value)
    return cliente


def test_escritas_publicas_vem_do_schema():
    """Guarda: se uma rota sair da lista, os testes abaixo param de cobri-la calados."""
    assert set(ESCRITAS_PUBLICAS) == {
        ("/api/cadastro/", "post"),
        ("/api/confirmar-email/1/", "post"),
        ("/api/reenviar-confirmacao/", "post"),
        ("/api/sessao/", "post"),
    }


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_LOGADAS)
def test_escrita_com_sessao_e_sem_csrf_da_403(cliente_com_sessao, rota, metodo):
    resposta = getattr(cliente_com_sessao, metodo)(rota)

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_LOGADAS)
def test_escrita_sem_sessao_da_401_mesmo_exigindo_csrf(rota, metodo):
    cliente = APIClient(enforce_csrf_checks=True)

    resposta = getattr(cliente, metodo)(rota)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_PUBLICAS)
def test_escrita_publica_sem_csrf_da_403(rota, metodo):
    """Login CSRF: sem sessão e sem token, a escrita pública é recusada."""
    cliente = APIClient(enforce_csrf_checks=True)

    resposta = getattr(cliente, metodo)(rota, {}, format="json")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_PUBLICAS)
def test_escrita_publica_com_sessao_e_sem_csrf_da_403(cliente_com_sessao, rota, metodo):
    """Logado, o CSRF é cobrado na autenticação, antes da permissão."""
    resposta = getattr(cliente_com_sessao, metodo)(rota, {}, format="json")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_PUBLICAS)
def test_escrita_publica_com_token_errado_da_403(rota, metodo):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get(ROTA_DO_COOKIE)
    cliente.credentials(HTTP_X_CSRFTOKEN="x" * 32)

    resposta = getattr(cliente, metodo)(rota, {}, format="json")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_PUBLICAS)
def test_escrita_publica_com_token_chega_na_view(cliente_com_token, rota, metodo, db):
    # db: a confirmação de e-mail consulta o token no banco (BE-06).
    resposta = getattr(cliente_com_token, metodo)(rota, {}, format="json")

    # Chegou na view: não foi barrada pelo CSRF nem pela autenticação.
    assert resposta.status_code not in (401, 403)


def test_rota_do_cookie_grava_o_csrftoken_sem_login():
    resposta = APIClient().get(ROTA_DO_COOKIE)

    assert resposta.status_code == 204
    cookie = resposta.cookies["csrftoken"]
    assert cookie.value
    # O apiClient do PWA lê o cookie com JavaScript (ADR 0007).
    assert not cookie["httponly"]


def test_motivo_do_csrf_recusado_vai_para_o_log_sem_o_path(caplog):
    """Diagnóstico em produção: cookie ausente ou origem que não confere.

    O path fica de fora: em /api/confirmar-email/{token}/ ele leva o token.
    """
    cliente = APIClient(enforce_csrf_checks=True)

    with caplog.at_level(logging.WARNING, logger="apps.cadastro.autenticacao"):
        cliente.post("/api/confirmar-email/token-secreto/", {}, format="json")

    mensagens = [r.getMessage() for r in caplog.records]
    assert any("CSRF recusado" in m and "cookie" in m.lower() for m in mensagens)
    assert not any("token-secreto" in m for m in mensagens)


def test_login_atras_do_proxy_https_passa_na_checagem_de_origem(
    settings, cliente_com_token, db
):
    """O Caddy encerra o HTTPS e encaminha em HTTP (ADR 0012).

    O navegador manda `Origin: https://...`. Sem SECURE_PROXY_SSL_HEADER, o
    Django acha que a requisição é HTTP, a origem não confere e todo login dá
    403 só em produção.

    `db`: o limite de taxa do login (#123) consulta o cache em banco antes da
    view.
    """
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    resposta = cliente_com_token.post(
        "/api/sessao/",
        {},
        format="json",
        # O Caddy repassa o Host original e diz que a conexão era HTTPS.
        HTTP_HOST="testserver",
        HTTP_ORIGIN="https://testserver",
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert resposta.status_code not in (401, 403)


def test_sem_o_cabecalho_do_proxy_a_origem_https_e_recusada(
    settings, cliente_com_token
):
    """Prova de que o teste acima depende mesmo do SECURE_PROXY_SSL_HEADER."""
    settings.SECURE_PROXY_SSL_HEADER = None

    resposta = cliente_com_token.post(
        "/api/sessao/",
        {},
        format="json",
        HTTP_HOST="testserver",
        HTTP_ORIGIN="https://testserver",
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"
