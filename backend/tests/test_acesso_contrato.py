"""Teste 6 do guia: acesso às rotas do contrato (BE-03, 3.1 e 4.2).

Rota logada sem sessão -> 401 com `nao_autenticado`.
Rota logada com sessão -> chega na view (que ainda responde 501).
Rota pública sem sessão -> chega na view (que ainda responde 501).
As rotas vêm do schema (tests/rotas_do_contrato.py), não de uma lista fixa.
"""

import pytest
from rest_framework.test import APIClient

from tests.rotas_do_contrato import ROTAS_LOGADAS, ROTAS_PUBLICAS


def test_schema_tem_as_rotas_esperadas():
    """Guarda: se a leitura do schema quebrar, os testes abaixo não viram vazios."""
    assert len(ROTAS_LOGADAS) == 8
    assert len(ROTAS_PUBLICAS) == 10


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

    # BE-05 em diante: trocar 501 pelo status de sucesso de cada rota.
    assert resposta.status_code == 501


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_PUBLICAS)
def test_rota_publica_responde_sem_login(rota, metodo):
    resposta = getattr(APIClient(), metodo)(rota)

    # BE-05 em diante: trocar 501 pelo status de sucesso de cada rota.
    assert resposta.status_code == 501
