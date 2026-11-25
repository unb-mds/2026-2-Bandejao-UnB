"""Fixtures do check-in (BE-09)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.fila.tests.apoio import RU_GAMA, criar_campus
from config.parametros import AvisoPrivacidadeConfig


@pytest.fixture
def conta(db):
    """Conta com o aviso de privacidade em dia (o `usuario` da raiz não está)."""
    return get_user_model().objects.create_user(
        matricula_siape="202400002",
        tipo_usuario="estudante",
        apelido="dani",
        email_institucional="202400002@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita=AvisoPrivacidadeConfig.versao_atual,
        password="senha-forte-123",
    )


@pytest.fixture
def darcy(db):
    return criar_campus()


@pytest.fixture
def gama(db):
    return criar_campus(nome="Gama", ru=RU_GAMA)
