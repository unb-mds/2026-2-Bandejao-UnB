"""CSRF nas rotas reais do contrato (BE-03, guia 4.1).

Quem tem sessão e escreve sem o token CSRF recebe 403 (CSRF recusado).
Quem não tem sessão recebe 401. Os dois nunca se confundem: um 403 de CSRF
não pode deslogar o usuário no front, e um 401 não pode parecer aviso de
privacidade pendente.
"""

import pytest
from rest_framework.test import APIClient

from tests.rotas_do_contrato import ESCRITAS_LOGADAS


@pytest.fixture
def cliente_com_sessao(usuario):
    """Cliente que EXIGE CSRF (como um navegador) e já tem sessão."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(usuario)
    return cliente


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_LOGADAS)
def test_escrita_com_sessao_e_sem_csrf_da_403(cliente_com_sessao, rota, metodo):
    resposta = getattr(cliente_com_sessao, metodo)(rota)

    assert resposta.status_code == 403
    # BE-05: quando o 403 de CSRF ganhar `codigo`, conferir o codigo aqui.
    assert "CSRF" in resposta.json()["detail"]


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_LOGADAS)
def test_escrita_sem_sessao_da_401_mesmo_exigindo_csrf(rota, metodo):
    cliente = APIClient(enforce_csrf_checks=True)

    resposta = getattr(cliente, metodo)(rota)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"
