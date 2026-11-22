"""Parâmetros de gamificação do Anexo A e do Nível 4."""

import re
from datetime import date

import pytest

from config import parametros


@pytest.mark.parametrize(
    ("atributo", "esperado"),
    [
        ("pontos_checkin", 10),
        ("pontos_resposta_saida", 15),
        ("pontos_avaliacao", 5),
        ("min_dias_semana", 3),
        ("bonus_semana", 20),
        ("limiares_patente", (0, 150, 450, 900, 1500)),
        ("tamanho_ranking", 10),
    ],
)
def test_parametros_de_gamificacao_correspondem_ao_anexo_a(atributo, esperado):
    configuracao = getattr(parametros, "ParametrosGamificacaoConfig", None)

    assert configuracao is not None, (
        "ParametrosGamificacaoConfig deve existir em config.parametros"
    )
    assert getattr(configuracao, atributo, None) == esperado


def test_termino_de_2026_2_e_14_de_dezembro():
    """14/12/2026, pelo calendário da UnB (decisão do grupo em 22/11/2026).

    Confere só a chave de 2026.2: cadastrar os próximos semestres não quebra
    este teste.
    """
    configuracao = getattr(parametros, "ParametrosGamificacaoConfig", None)

    assert configuracao is not None, (
        "ParametrosGamificacaoConfig deve existir em config.parametros"
    )
    datas = getattr(configuracao, "datas_termino_semestre", None)
    assert datas["2026.2"] == date(2026, 12, 14)


def test_semestre_inicial_e_2026_2():
    """Usado só quando não há nenhuma data de término configurada (RN12)."""
    configuracao = parametros.ParametrosGamificacaoConfig

    assert getattr(configuracao, "semestre_inicial", None) == "2026.2"


def test_rotulos_de_semestre_bem_formados():
    """Um rótulo como "2026-2" quebraria o cálculo do semestre seguinte, e
    "2026.3" viraria "2027.1" sem erro: a partir do dia seguinte ao último
    término, todo check-in e toda avaliação dependem desse cálculo."""
    configuracao = parametros.ParametrosGamificacaoConfig
    rotulos = [configuracao.semestre_inicial, *configuracao.datas_termino_semestre]

    for rotulo in rotulos:
        assert re.fullmatch(r"\d{4}\.[12]", rotulo), rotulo


def test_ordem_das_datas_e_a_ordem_dos_rotulos():
    """O término de cada semestre vem depois do término do anterior."""
    datas = parametros.ParametrosGamificacaoConfig.datas_termino_semestre

    por_data = sorted(datas, key=datas.get)

    assert por_data == sorted(datas)
    assert len(set(datas.values())) == len(datas)
