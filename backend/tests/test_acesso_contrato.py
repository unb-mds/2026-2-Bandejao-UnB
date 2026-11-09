"""Teste 6 do guia: acesso às rotas do contrato (BE-03, 3.1 e 4.2).

Rota logada sem sessão -> 401 com `nao_autenticado`.
Rota logada com sessão -> chega na view (não é barrada com 401/403).
Rota pública sem sessão -> chega na view (não é barrada com 401/403).
As rotas vêm do schema (tests/rotas_do_contrato.py), não de uma lista fixa.
"""

import pytest
from rest_framework.test import APIClient

from tests.rotas_do_contrato import ROTAS_LOGADAS, ROTAS_PUBLICAS


def test_schema_tem_as_rotas_esperadas():
    """Guarda: se a leitura do schema quebrar, os testes abaixo não viram vazios.

    A quantidade exata de rotas já é conferida por
    `test_contrato_tem_so_os_endpoints_da_v1` (igualdade com ENDPOINTS_V1).
    """
    assert ROTAS_LOGADAS
    assert ROTAS_PUBLICAS


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_LOGADAS)
def test_rota_logada_sem_sessao_da_401(rota, metodo):
    resposta = getattr(APIClient(), metodo)(rota)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_LOGADAS)
def test_rota_logada_com_sessao_chega_na_view(usuario, rota, metodo):
    """Pega permissão restritiva demais (ex.: IsAdminUser), que o yaml não mostra."""
    cliente = APIClient()
    cliente.force_login(usuario)

    resposta = getattr(cliente, metodo)(rota)

    # Chegou na view: não foi barrada por autenticação nem por permissão.
    # Hoje a view responde 501; depois do BE-05, sem corpo e sem dados no banco,
    # 2xx, 400 ou 404 também servem.
    assert resposta.status_code not in (401, 403)


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_PUBLICAS)
def test_rota_publica_responde_sem_login(rota, metodo):
    """Pega rota pública que perdeu o AllowAny."""
    resposta = getattr(APIClient(), metodo)(rota)

    # Chegou na view: não foi barrada por autenticação nem por permissão.
    # Hoje a view responde 501; depois do BE-05, sem corpo e sem dados no banco,
    # 2xx, 400 ou 404 também servem.
    assert resposta.status_code not in (401, 403)
