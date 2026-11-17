"""TentativaLoginTracker (RF03.2, Anexo A, Cadastro N4 4c).

5 tentativas malsucedidas em 10 minutos bloqueiam o login por 10 minutos.
Os dados ficam na própria conta: `tentativas_login_falhas`,
`primeira_falha_login_em` e `bloqueado_ate`.
"""

from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cadastro.tentativa_login_tracker import TentativaLoginTracker
from config.parametros import ParametrosCadastroConfig

AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def tracker():
    return TentativaLoginTracker()


@pytest.fixture
def outra_conta(db):
    return get_user_model().objects.create_user(
        matricula_siape="1234567",
        tipo_usuario="professor_servidor",
        apelido="dani",
        email_institucional="dani@unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )


@pytest.fixture
def relogio():
    """`relogio.return_value = ...` avança o tempo do teste."""
    with mock.patch("django.utils.timezone.now", return_value=AGORA) as agora:
        yield agora


def falhar(tracker, conta, vezes):
    for _ in range(vezes):
        tracker.registrar_tentativa(conta, sucesso=False)


def test_parametros_do_anexo_a():
    assert ParametrosCadastroConfig.login_max_tentativas == 5
    assert ParametrosCadastroConfig.login_janela == timedelta(minutes=10)
    assert ParametrosCadastroConfig.login_bloqueio == timedelta(minutes=10)


def test_conta_nova_nao_esta_bloqueada(tracker, usuario, relogio):
    assert not tracker.esta_bloqueado(usuario)


def test_quatro_falhas_nao_bloqueiam(tracker, usuario, relogio):
    falhar(tracker, usuario, 4)

    assert not tracker.esta_bloqueado(usuario)
    usuario.refresh_from_db()
    assert usuario.tentativas_login_falhas == 4
    assert usuario.bloqueado_ate is None


def test_quinta_falha_em_10_minutos_bloqueia_por_10_minutos(tracker, usuario, relogio):
    falhar(tracker, usuario, 4)
    relogio.return_value = AGORA + timedelta(minutes=9)

    falhar(tracker, usuario, 1)

    assert tracker.esta_bloqueado(usuario)
    usuario.refresh_from_db()
    assert usuario.bloqueado_ate == AGORA + timedelta(minutes=19)


def test_bloqueio_vale_ate_o_ultimo_instante(tracker, usuario, relogio):
    falhar(tracker, usuario, 5)

    relogio.return_value = AGORA + timedelta(minutes=10) - timedelta(seconds=1)
    assert tracker.esta_bloqueado(usuario)

    relogio.return_value = AGORA + timedelta(minutes=10)
    assert not tracker.esta_bloqueado(usuario)


def test_falha_depois_da_janela_comeca_uma_contagem_nova(tracker, usuario, relogio):
    """Falhas espalhadas (4 agora, 1 depois de 10 min) não bloqueiam."""
    falhar(tracker, usuario, 4)
    relogio.return_value = AGORA + timedelta(minutes=10)

    falhar(tracker, usuario, 1)

    assert not tracker.esta_bloqueado(usuario)
    usuario.refresh_from_db()
    assert usuario.tentativas_login_falhas == 1
    assert usuario.primeira_falha_login_em == AGORA + timedelta(minutes=10)


def test_janela_conta_da_primeira_falha(tracker, usuario, relogio):
    """A janela não desliza: começa na primeira falha da sequência."""
    falhar(tracker, usuario, 1)
    relogio.return_value = AGORA + timedelta(minutes=8)
    falhar(tracker, usuario, 3)
    relogio.return_value = AGORA + timedelta(minutes=11)

    falhar(tracker, usuario, 1)

    assert not tracker.esta_bloqueado(usuario)


def test_acerto_zera_a_contagem(tracker, usuario, relogio):
    falhar(tracker, usuario, 4)

    tracker.registrar_tentativa(usuario, sucesso=True)
    falhar(tracker, usuario, 4)

    assert not tracker.esta_bloqueado(usuario)
    usuario.refresh_from_db()
    assert usuario.tentativas_login_falhas == 4


def test_acerto_limpa_todos_os_campos(tracker, usuario, relogio):
    falhar(tracker, usuario, 2)

    tracker.registrar_tentativa(usuario, sucesso=True)

    usuario.refresh_from_db()
    assert usuario.tentativas_login_falhas == 0
    assert usuario.primeira_falha_login_em is None
    assert usuario.bloqueado_ate is None


def test_depois_do_bloqueio_a_contagem_recomeca(tracker, usuario, relogio):
    falhar(tracker, usuario, 5)
    relogio.return_value = AGORA + timedelta(minutes=10)

    falhar(tracker, usuario, 4)

    assert not tracker.esta_bloqueado(usuario)
    falhar(tracker, usuario, 1)
    assert tracker.esta_bloqueado(usuario)


def test_contagem_e_por_conta(tracker, usuario, outra_conta, relogio):
    falhar(tracker, usuario, 5)

    assert tracker.esta_bloqueado(usuario)
    assert not tracker.esta_bloqueado(outra_conta)


def test_segundos_restantes_do_bloqueio(tracker, usuario, relogio):
    falhar(tracker, usuario, 5)
    relogio.return_value = AGORA + timedelta(minutes=3, seconds=30)

    assert tracker.segundos_restantes(usuario) == 6 * 60 + 30


def test_segundos_restantes_sem_bloqueio_e_zero(tracker, usuario, relogio):
    assert tracker.segundos_restantes(usuario) == 0


def test_grava_so_os_campos_do_bloqueio(tracker, usuario, relogio):
    """Não sobrescreve o resto da conta com uma cópia velha da memória."""
    get_user_model().objects.filter(pk=usuario.pk).update(status="suspenso")

    falhar(tracker, usuario, 1)

    usuario.refresh_from_db()
    assert usuario.status == "suspenso"
