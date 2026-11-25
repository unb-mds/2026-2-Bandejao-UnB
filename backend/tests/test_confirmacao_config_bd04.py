"""A confirmação de e-mail deve consumir a validade configurada."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from apps.cadastro.confirmacao_email_service import ConfirmacaoEmailService
from apps.cadastro.management.commands.excluir_cadastros_pendentes import (
    ExclusaoCadastroPendenteJob,
)
from apps.cadastro.models import TipoToken, Token
from config.parametros import ParametrosCadastroConfig


@pytest.mark.django_db
def test_token_e_email_respeitam_validade_configurada(monkeypatch, usuario, mailoutbox):
    agora = datetime(2026, 11, 16, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(
        ParametrosCadastroConfig,
        "validade_confirmacao_email",
        timedelta(hours=6),
    )
    monkeypatch.setattr(
        "apps.cadastro.confirmacao_email_service.timezone.now",
        lambda: agora,
    )

    ConfirmacaoEmailService().enviar_link(usuario)

    token = Token.objects.get(
        usuario=usuario,
        tipo=TipoToken.CONFIRMACAO_EMAIL,
    )
    assert token.expira_em == agora + timedelta(hours=6)
    assert len(mailoutbox) == 1
    assert "O link vale por 6 horas" in mailoutbox[0].body


def test_exclusao_de_pendentes_respeita_validade_configurada(monkeypatch):
    agora = datetime(2026, 11, 16, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(
        ParametrosCadastroConfig,
        "validade_confirmacao_email",
        timedelta(hours=6),
    )
    monkeypatch.setattr(
        "apps.cadastro.management.commands.excluir_cadastros_pendentes.timezone.now",
        lambda: agora,
    )
    repositorio = Mock()
    repositorio.pendentes_expiradas.return_value = []
    job = ExclusaoCadastroPendenteJob()
    job.conta_repository = repositorio

    assert job.executar() == 0

    repositorio.pendentes_expiradas.assert_called_once_with(agora - timedelta(hours=6))
