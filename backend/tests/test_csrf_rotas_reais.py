"""CSRF nas rotas reais do contrato (BE-03, guia 4.1).

Quem tem sessão e escreve sem o token CSRF recebe 403 (CSRF recusado).
Quem não tem sessão recebe 401. Os dois nunca se confundem: um 403 de CSRF
não pode deslogar o usuário no front, e um 401 não pode parecer aviso de
privacidade pendente.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

ESCRITAS_LOGADAS = [
    ("/api/sessao/", "delete"),
    ("/api/privacidade/aceite/", "post"),
    ("/api/avaliacoes/", "post"),
    ("/api/checkins/", "post"),
    ("/api/gamificacao/adesao/", "post"),
    ("/api/gamificacao/adesao/", "delete"),
]


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
def cliente_com_sessao(usuario):
    """Cliente que EXIGE CSRF (como um navegador) e já tem sessão."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(usuario)
    return cliente


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_LOGADAS)
def test_escrita_com_sessao_e_sem_csrf_da_403(cliente_com_sessao, rota, metodo):
    resposta = getattr(cliente_com_sessao, metodo)(rota)

    assert resposta.status_code == 403


@pytest.mark.parametrize(("rota", "metodo"), ESCRITAS_LOGADAS)
def test_escrita_sem_sessao_da_401_mesmo_exigindo_csrf(rota, metodo):
    cliente = APIClient(enforce_csrf_checks=True)

    resposta = getattr(cliente, metodo)(rota)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"
