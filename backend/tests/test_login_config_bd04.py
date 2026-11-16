"""O bloqueio de login deve consumir os parâmetros do Anexo A."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from apps.cadastro.models import Usuario
from apps.cadastro.tentativa_login_tracker import TentativaLoginTracker
from config.parametros import ParametrosCadastroConfig

AGORA = datetime(2026, 11, 16, 15, 0, tzinfo=UTC)


@pytest.fixture
def conta(monkeypatch):
    usuario = Usuario(
        pk=1,
        tentativas_login_falhas=0,
        primeira_falha_login_em=AGORA,
        bloqueado_ate=None,
    )
    monkeypatch.setattr(usuario, "save", Mock())
    monkeypatch.setattr(
        "apps.cadastro.tentativa_login_tracker.timezone.now",
        lambda: AGORA,
    )
    return usuario


def test_login_bloqueia_no_limite_configurado(monkeypatch, conta):
    monkeypatch.setattr(ParametrosCadastroConfig, "login_max_tentativas", 2)
    conta.tentativas_login_falhas = 1

    TentativaLoginTracker().registrar_tentativa(conta, sucesso=False)

    assert conta.tentativas_login_falhas == 2
    assert conta.bloqueado_ate == AGORA + ParametrosCadastroConfig.login_bloqueio


def test_login_reinicia_contagem_apos_janela_configurada(monkeypatch, conta):
    monkeypatch.setattr(ParametrosCadastroConfig, "login_janela", timedelta(minutes=2))
    conta.tentativas_login_falhas = 4
    conta.primeira_falha_login_em = AGORA - timedelta(minutes=3)

    TentativaLoginTracker().registrar_tentativa(conta, sucesso=False)

    assert conta.tentativas_login_falhas == 1
    assert conta.primeira_falha_login_em == AGORA
    assert conta.bloqueado_ate is None


def test_login_aplica_duracao_de_bloqueio_configurada(monkeypatch, conta):
    monkeypatch.setattr(
        ParametrosCadastroConfig, "login_bloqueio", timedelta(minutes=30)
    )
    conta.tentativas_login_falhas = 4

    TentativaLoginTracker().registrar_tentativa(conta, sucesso=False)

    assert conta.bloqueado_ate == AGORA + timedelta(minutes=30)
