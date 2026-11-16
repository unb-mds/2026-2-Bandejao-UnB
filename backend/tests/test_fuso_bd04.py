"""Fuso de Brasília exigido pela BD-04 (#90) e pelo Anexo A."""

from datetime import UTC, datetime

from django.conf import settings
from django.utils import timezone


def test_datas_e_horas_usam_fuso_horario():
    assert settings.USE_TZ is True


def test_fuso_padrao_e_o_de_sao_paulo():
    assert settings.TIME_ZONE == "America/Sao_Paulo"


def test_inicio_do_dia_utc_ainda_pertence_ao_dia_anterior_em_brasilia():
    instante = datetime(2026, 11, 16, 0, 30, tzinfo=UTC)

    horario_local = timezone.localtime(
        instante,
        timezone=timezone.get_default_timezone(),
    )

    assert horario_local.date().isoformat() == "2026-11-15"
    assert (horario_local.hour, horario_local.minute) == (21, 30)