"""Fixtures da avaliação (BE-13).

O dia dos testes é a terça 24/11/2026 (horário de Brasília), com o almoço de
11h00 às 14h30 (Anexo A).
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.avaliacao.tests.apoio import TERCA
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_campus, criar_refeicao


def criar_conta(numero, apelido):
    return get_user_model().objects.create_user(
        matricula_siape=f"2024000{numero:02d}",
        tipo_usuario="estudante",
        apelido=apelido,
        email_institucional=f"2024000{numero:02d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )


@pytest.fixture
def conta(db):
    return criar_conta(11, "dani")


@pytest.fixture
def outra_conta(db):
    return criar_conta(12, "rafa")


@pytest.fixture
def gama(db):
    return criar_campus()


@pytest.fixture
def almoco(gama):
    return criar_refeicao(gama, TERCA, TipoRefeicao.ALMOCO)


@pytest.fixture
def logado(conta):
    """Cliente com sessão e CSRF, como o navegador (#112)."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(conta)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    return cliente
