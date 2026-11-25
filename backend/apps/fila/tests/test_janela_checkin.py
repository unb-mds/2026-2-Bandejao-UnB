"""Janela de horário do check-in (BE-09, RF11, Anexo A, Fila N4 4a).

Os horários do Anexo A são de Brasília: o validador converte o `agora` (UTC,
como o `timezone.now()`) para o horário local antes de comparar.
"""

from datetime import UTC, datetime, time, timedelta

import pytest

from apps.cardapio.models import TipoRefeicao
from apps.fila.janela_checkin_validator import JanelaCheckinValidator
from config.parametros import HorariosRefeicaoConfig

BRASILIA = timedelta(hours=-3)


def em_brasilia(hora: time) -> datetime:
    """`hora` de Brasília em 17/11/2026, como datetime em UTC."""
    local = datetime.combine(datetime(2026, 11, 17).date(), hora)
    return (local - BRASILIA).replace(tzinfo=UTC)


@pytest.mark.parametrize(
    "tipo, horario",
    [
        (TipoRefeicao.CAFE, HorariosRefeicaoConfig.horario_cafe),
        (TipoRefeicao.ALMOCO, HorariosRefeicaoConfig.horario_almoco),
        (TipoRefeicao.JANTAR, HorariosRefeicaoConfig.horario_jantar),
    ],
)
def test_inicio_e_fim_da_refeicao_estao_dentro(tipo, horario):
    inicio, fim = horario
    validador = JanelaCheckinValidator()

    assert validador.dentro_do_horario(tipo, em_brasilia(inicio)) is True
    assert validador.dentro_do_horario(tipo, em_brasilia(fim)) is True


@pytest.mark.parametrize(
    "tipo, horario",
    [
        (TipoRefeicao.CAFE, HorariosRefeicaoConfig.horario_cafe),
        (TipoRefeicao.ALMOCO, HorariosRefeicaoConfig.horario_almoco),
        (TipoRefeicao.JANTAR, HorariosRefeicaoConfig.horario_jantar),
    ],
)
def test_um_minuto_antes_e_depois_estao_fora(tipo, horario):
    inicio, fim = horario
    validador = JanelaCheckinValidator()
    antes = em_brasilia(inicio) - timedelta(minutes=1)
    depois = em_brasilia(fim) + timedelta(minutes=1)

    assert validador.dentro_do_horario(tipo, antes) is False
    assert validador.dentro_do_horario(tipo, depois) is False


def test_almoco_fora_do_horario_do_almoco_mesmo_dentro_do_jantar():
    assert (
        JanelaCheckinValidator().dentro_do_horario(
            TipoRefeicao.ALMOCO, em_brasilia(time(18, 0))
        )
        is False
    )


def test_compara_no_horario_de_brasilia_e_nao_em_utc():
    """12h em UTC são 9h em Brasília: café, e não almoço."""
    meio_dia_utc = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    validador = JanelaCheckinValidator()

    assert validador.dentro_do_horario(TipoRefeicao.CAFE, meio_dia_utc) is True
    assert validador.dentro_do_horario(TipoRefeicao.ALMOCO, meio_dia_utc) is False
