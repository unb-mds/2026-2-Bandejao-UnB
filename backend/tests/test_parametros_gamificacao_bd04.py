"""Parâmetros de gamificação do Anexo A e do Nível 4."""

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


def test_datas_de_termino_semestre_com_o_termino_de_2026_2():
    """14/12/2026, pelo calendário da UnB (decisão do grupo em 22/11/2026)."""
    configuracao = getattr(parametros, "ParametrosGamificacaoConfig", None)

    assert configuracao is not None, (
        "ParametrosGamificacaoConfig deve existir em config.parametros"
    )
    assert getattr(configuracao, "datas_termino_semestre", None) == {
        "2026.2": date(2026, 12, 14)
    }


def test_semestre_inicial_e_o_semestre_atual():
    """Sem nenhuma data configurada, o semestre é 2026.2 (RN12, BE-14)."""
    configuracao = parametros.ParametrosGamificacaoConfig

    assert getattr(configuracao, "semestre_inicial", None) == "2026.2"
