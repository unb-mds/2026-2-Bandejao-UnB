"""Os passos da previsão que não leem o banco (BE-15, RF13, RN06, Fila N4 4c).

Janela de 4 semanas, faixas de 15 min, suficiência de dias, média por faixa
e classificação pelos cortes de 25/50/75%. Cada um é testado sozinho, sem
banco, PDF nem interface.
"""

from datetime import date, time
from fractions import Fraction
from itertools import pairwise
from unittest import mock

import pytest

from apps.cardapio.models import TipoRefeicao
from apps.fila.checkin_repository import ContagemDia
from apps.fila.classificador_nivel_fila import ClassificadorNivelFila, NivelFila
from apps.fila.faixa_horario_generator import FaixaHorario, FaixaHorarioGenerator
from apps.fila.janela_historico_resolver import JanelaHistoricoResolver
from apps.fila.media_por_faixa_calculator import MediaPorFaixaCalculator
from apps.fila.suficiencia_dados_validator import SuficienciaDadosValidator
from apps.fila.tests.apoio_previsao import JANELA, QUARTA
from config.parametros import HorariosRefeicaoConfig, ParametrosFilaConfig


def dia(n, *por_faixa):
    """`ContagemDia` de um dia qualquer da janela (o n-ésimo)."""
    return ContagemDia(data=JANELA[n], checkins_por_faixa=list(por_faixa))


# --- 1. JanelaHistoricoResolver ----------------------------------------------


def test_janela_sao_as_4_semanas_anteriores_no_mesmo_dia_da_semana():
    assert JanelaHistoricoResolver().datas_da_janela(QUARTA) == JANELA


def test_janela_nao_inclui_o_proprio_dia():
    """O dia pedido ainda pode estar acontecendo: a previsão é do histórico."""
    assert QUARTA not in JanelaHistoricoResolver().datas_da_janela(QUARTA)


def test_janela_mantem_o_dia_da_semana_na_virada_do_ano():
    datas = JanelaHistoricoResolver().datas_da_janela(date(2027, 1, 13))

    assert datas[-1] == date(2026, 12, 16)
    assert {d.weekday() for d in datas} == {date(2027, 1, 13).weekday()}


def test_janela_le_as_semanas_da_configuracao():
    with mock.patch.object(ParametrosFilaConfig, "janela_semanas", 2):
        assert JanelaHistoricoResolver().datas_da_janela(QUARTA) == JANELA[:2]


# --- 2. FaixaHorarioGenerator -------------------------------------------------


def test_faixas_do_almoco_cobrem_11h00_a_14h30_de_15_em_15_min():
    faixas = FaixaHorarioGenerator().faixas(TipoRefeicao.ALMOCO)

    assert len(faixas) == 14
    assert faixas[0] == FaixaHorario(inicio=time(11, 0), fim=time(11, 15))
    assert faixas[-1] == FaixaHorario(inicio=time(14, 15), fim=time(14, 30))
    # Sem buraco nem sobreposição.
    for anterior, seguinte in pairwise(faixas):
        assert anterior.fim == seguinte.inicio


@pytest.mark.parametrize(
    "tipo, horario",
    [
        (TipoRefeicao.CAFE, HorariosRefeicaoConfig.horario_cafe),
        (TipoRefeicao.ALMOCO, HorariosRefeicaoConfig.horario_almoco),
        (TipoRefeicao.JANTAR, HorariosRefeicaoConfig.horario_jantar),
    ],
)
def test_faixas_comecam_e_terminam_no_horario_da_refeicao(tipo, horario):
    faixas = FaixaHorarioGenerator().faixas(tipo)

    assert (faixas[0].inicio, faixas[-1].fim) == horario


def test_cafe_e_jantar_tem_10_faixas():
    gerador = FaixaHorarioGenerator()

    assert len(gerador.faixas(TipoRefeicao.CAFE)) == 10
    assert len(gerador.faixas(TipoRefeicao.JANTAR)) == 10


def test_ultima_faixa_e_cortada_no_fim_da_refeicao():
    """Horário que não fecha em 15 min: a última faixa termina com a refeição."""
    with mock.patch.object(
        HorariosRefeicaoConfig, "horario_almoco", (time(11, 0), time(11, 40))
    ):
        faixas = FaixaHorarioGenerator().faixas(TipoRefeicao.ALMOCO)

    assert faixas[-1] == FaixaHorario(inicio=time(11, 30), fim=time(11, 40))


def test_faixas_leem_o_tamanho_da_configuracao():
    with mock.patch.object(ParametrosFilaConfig, "faixa_minutos", 30):
        faixas = FaixaHorarioGenerator().faixas(TipoRefeicao.ALMOCO)

    assert len(faixas) == 7
    assert faixas[1] == FaixaHorario(inicio=time(11, 30), fim=time(12, 0))


# --- 4. SuficienciaDadosValidator ---------------------------------------------


def test_dois_dias_com_dados_sao_insuficientes():
    assert SuficienciaDadosValidator().suficiente([dia(0, 5), dia(1, 5)]) is False


def test_tres_dias_com_dados_sao_suficientes():
    assert (
        SuficienciaDadosValidator().suficiente([dia(0, 1), dia(1, 1), dia(2, 1)])
        is True
    )


def test_nenhum_dia_e_insuficiente():
    assert SuficienciaDadosValidator().suficiente([]) is False


def test_dia_sem_checkin_nao_conta_como_dia_com_dados():
    """Um dia só com zeros não é dia com dados (RN06)."""
    assert (
        SuficienciaDadosValidator().suficiente([dia(0, 1), dia(1, 1), dia(2, 0, 0)])
        is False
    )


def test_suficiencia_le_o_minimo_da_configuracao():
    with mock.patch.object(ParametrosFilaConfig, "min_dias_distintos", 2):
        assert SuficienciaDadosValidator().suficiente([dia(0, 1), dia(1, 1)]) is True


# --- 5. MediaPorFaixaCalculator -----------------------------------------------


def test_media_divide_pelo_numero_de_dias_com_dados():
    medias = MediaPorFaixaCalculator().calcular(
        [dia(0, 2, 6), dia(1, 4, 0), dia(2, 0, 3)]
    )

    assert medias == [Fraction(2), Fraction(3)]


def test_faixa_vazia_num_dia_com_dados_conta_como_zero():
    """A outra leitura (ignorar o dia só para a faixa vazia) daria 9 na
    segunda faixa, e ela viraria pico com um dia atípico (RN06, L08)."""
    medias = MediaPorFaixaCalculator().calcular(
        [dia(0, 3, 9), dia(1, 3, 0), dia(2, 3, 0)]
    )

    assert medias == [Fraction(3), Fraction(3)]


def test_media_e_exata_sem_erro_de_arredondamento():
    medias = MediaPorFaixaCalculator().calcular([dia(0, 1), dia(1, 0), dia(2, 0)])

    assert medias == [Fraction(1, 3)]


# --- 6. ClassificadorNivelFila -----------------------------------------------


@pytest.mark.parametrize(
    "media, nivel",
    [
        (0, NivelFila.VAZIA),
        (24, NivelFila.VAZIA),
        (25, NivelFila.CURTA),
        (49, NivelFila.CURTA),
        (50, NivelFila.MODERADA),
        (74, NivelFila.MODERADA),
        (75, NivelFila.LONGA),
        (100, NivelFila.LONGA),
    ],
)
def test_cortes_de_25_50_e_75_por_cento_da_faixa_mais_cheia(media, nivel):
    assert ClassificadorNivelFila().classificar(Fraction(media), Fraction(100)) is (
        nivel
    )


def test_corte_exato_com_media_fracionaria_nao_cai_para_o_nivel_de_baixo():
    """1 de 4/3 é 75%: com float, 1.0 / 1.333… daria 0.7499…."""
    assert ClassificadorNivelFila().classificar(Fraction(1), Fraction(4, 3)) is (
        NivelFila.LONGA
    )


def test_niveis_tem_os_valores_do_contrato():
    assert [nivel.value for nivel in NivelFila] == [
        "vazia",
        "curta",
        "moderada",
        "longa",
    ]


def test_cortes_vem_da_configuracao():
    with mock.patch.object(ParametrosFilaConfig, "cortes", (10, 20, 30)):
        assert ClassificadorNivelFila().classificar(Fraction(30), Fraction(100)) is (
            NivelFila.LONGA
        )


def test_mais_chegadas_numa_faixa_nunca_baixam_o_nivel_dela():
    """Propriedade do plano de testes: com a faixa mais cheia fixa, subir a
    média de uma faixa nunca a leva para um nível mais baixo."""
    ordem = list(NivelFila)
    classificador = ClassificadorNivelFila()
    maxima = Fraction(40, 3)
    niveis = [
        ordem.index(classificador.classificar(Fraction(n, 3), maxima))
        for n in range(41)
    ]

    assert niveis == sorted(niveis)
