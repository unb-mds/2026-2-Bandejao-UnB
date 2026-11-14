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
    """Guarda: se a leitura do schema quebrar, os testes abaixo não viram vazios."""
    assert ("/api/sessao/", "post") in ESCRITAS_PUBLICAS
    assert ("/api/cadastro/", "post") in ESCRITAS_PUBLICAS


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
def test_escrita_publica_com_token_errado_da_403(rota, metodo):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get(ROTA_DO_COOKIE)
    cliente.credentials(HTTP_X_CSRFTOKEN="x" * 32)

    resposta = getattr(cliente, metodo)(rota, {}, format="json")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_PUBLICAS)
def test_escrita_publica_com_token_chega_na_view(cliente_com_token, rota, metodo):
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
