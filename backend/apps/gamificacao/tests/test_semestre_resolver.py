"""SemestreResolver (Gamificação N4 4a, RN12).

Cada semestre vai do dia seguinte ao término do anterior até o próprio
término. Depois do último término configurado, a data já é do semestre
seguinte, que fica aberto até alguém configurar o término dele.

As datas vão pelo construtor, para os testes não dependerem da config global
(menos os dois que conferem a config real).
"""

from datetime import date

import pytest

from apps.gamificacao.semestre_resolver import SemestreResolver
from config.parametros import ParametrosGamificacaoConfig

DATAS = {
    # Fora de ordem de propósito: o resolver ordena pelas datas.
    "2027.1": date(2027, 7, 10),
    "2026.2": date(2026, 12, 14),
}


def resolver(datas=DATAS, inicial="2026.2"):
    return SemestreResolver(datas=datas, inicial=inicial)


def test_data_dentro_do_semestre():
    assert resolver().semestre_de(date(2026, 11, 24)) == "2026.2"


def test_data_dentro_do_segundo_semestre_configurado():
    assert resolver().semestre_de(date(2027, 3, 1)) == "2027.1"


def test_dia_do_termino_ainda_e_o_mesmo_semestre():
    assert resolver().semestre_de(date(2026, 12, 14)) == "2026.2"


def test_dia_seguinte_ao_termino_ja_e_o_semestre_seguinte():
    """Pontos nas férias contam para o semestre seguinte."""
    assert resolver().semestre_de(date(2026, 12, 15)) == "2027.1"


def test_depois_do_ultimo_termino_e_o_semestre_seguinte_ao_ultimo():
    """Período aberto: ainda não há data de término do 2027.2."""
    assert resolver().semestre_de(date(2027, 7, 11)) == "2027.2"
    assert resolver().semestre_de(date(2028, 5, 1)) == "2027.2"


@pytest.mark.parametrize(
    ("ultimo", "seguinte"),
    [("2026.2", "2027.1"), ("2027.1", "2027.2"), ("2029.2", "2030.1")],
)
def test_virada_de_semestre_e_de_ano(ultimo, seguinte):
    datas = {ultimo: date(2026, 1, 1)}

    assert resolver(datas=datas).semestre_de(date(2026, 1, 2)) == seguinte


def test_sem_data_de_termino_o_semestre_e_o_inicial():
    """Semestre sem data configurada: o atual, 2026.2 (decisão de 22/11)."""
    sem_datas = resolver(datas={})

    assert sem_datas.semestre_de(date(2026, 11, 24)) == "2026.2"
    assert sem_datas.semestre_de(date(2027, 6, 1)) == "2026.2"


def test_padrao_vem_da_config():
    padrao = SemestreResolver()

    assert padrao.datas == ParametrosGamificacaoConfig.datas_termino_semestre
    assert padrao.inicial == ParametrosGamificacaoConfig.semestre_inicial


def test_config_real_termina_2026_2_em_14_de_dezembro():
    padrao = SemestreResolver()

    assert padrao.semestre_de(date(2026, 12, 14)) == "2026.2"
    assert padrao.semestre_de(date(2026, 12, 15)) == "2027.1"
