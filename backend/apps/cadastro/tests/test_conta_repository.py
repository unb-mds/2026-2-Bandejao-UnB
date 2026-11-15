"""Consultas de duplicidade da conta (RF01.5, Cadastro N4 4a)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cadastro.conta_repository import ContaRepository


@pytest.fixture
def conta(db):
    return get_user_model().objects.create_user(
        matricula_siape="251098732",
        tipo_usuario="estudante",
        apelido="cris",
        email_institucional="251098732@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="2026-11-14",
        password="senha-forte-123",
    )


def test_existe_matricula_ou_siape(conta):
    repositorio = ContaRepository()

    assert repositorio.existe_matricula_ou_siape("251098732")
    assert not repositorio.existe_matricula_ou_siape("251098733")


def test_existe_email_sem_distinguir_maiusculas_nem_espacos(conta):
    repositorio = ContaRepository()

    assert repositorio.existe_email(" 251098732@ALUNO.unb.br ")
    assert not repositorio.existe_email("251098733@aluno.unb.br")


def test_conta_pendente_tambem_conta_como_existente(conta):
    """RF01.5: a unicidade vale para conta confirmada ou pendente."""
    assert conta.status == "pendente"
    assert ContaRepository().existe_email(conta.email_institucional)
