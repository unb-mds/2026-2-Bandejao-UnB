"""Consultas da conta (RF01.5, Cadastro N4 4a; login pelo e-mail, 4c)."""

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
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


def test_buscar_por_email_acha_a_conta_sem_distinguir_maiusculas_nem_espacos(conta):
    repositorio = ContaRepository()

    assert repositorio.buscar_por_email("251098732@aluno.unb.br") == conta
    assert repositorio.buscar_por_email(" 251098732@ALUNO.unb.br ") == conta


def test_buscar_por_email_sem_conta_devolve_none(conta):
    repositorio = ContaRepository()

    assert repositorio.buscar_por_email("251098733@aluno.unb.br") is None
    # A matrícula pura não é e-mail: não acha a conta.
    assert repositorio.buscar_por_email("251098732") is None


def test_buscar_por_email_com_trava_devolve_a_conta(conta):
    """No SQLite a trava não tem efeito; aqui só confere que a busca funciona."""
    with transaction.atomic():
        achada = ContaRepository().buscar_por_email(
            "251098732@aluno.unb.br", travar=True
        )

    assert achada == conta


def test_buscar_por_identificador_saiu_do_repositorio():
    """BE-20: o login e o reenvio passaram a buscar pelo e-mail."""
    assert not hasattr(ContaRepository, "buscar_por_identificador")


def test_conta_pendente_tambem_conta_como_existente(conta):
    """RF01.5: a unicidade vale para conta confirmada ou pendente."""
    assert conta.status == "pendente"
    assert ContaRepository().existe_email(conta.email_institucional)


def test_registrar_aceite_se_pendente_grava_versao_e_hora(conta):
    agora = timezone.now()

    gravou = ContaRepository().registrar_aceite_se_pendente(conta, "2026-12-01", agora)

    assert gravou is True
    conta.refresh_from_db()
    assert conta.versao_aviso_aceita == "2026-12-01"
    assert conta.aceite_privacidade_em == agora


def test_registrar_aceite_se_pendente_nao_regrava_a_mesma_versao(conta):
    """A conferência e a escrita são um UPDATE só: a cópia velha não importa."""
    primeiro = timezone.now()
    copia_velha = get_user_model().objects.get(pk=conta.pk)
    ContaRepository().registrar_aceite_se_pendente(conta, "2026-12-01", primeiro)

    gravou = ContaRepository().registrar_aceite_se_pendente(
        copia_velha, "2026-12-01", timezone.now()
    )

    assert gravou is False
    conta.refresh_from_db()
    assert conta.aceite_privacidade_em == primeiro


def test_registrar_aceite_se_pendente_grava_so_os_campos_do_aviso(conta):
    get_user_model().objects.filter(pk=conta.pk).update(status="ativo")

    ContaRepository().registrar_aceite_se_pendente(conta, "2026-12-01", timezone.now())

    conta.refresh_from_db()
    assert conta.status == "ativo"
