"""Parâmetros de gamificação do Anexo A e do Nível 4."""

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


def test_datas_de_termino_semestre_sem_datas_confirmadas():
    configuracao = getattr(parametros, "ParametrosGamificacaoConfig", None)

    assert configuracao is not None, (
        "ParametrosGamificacaoConfig deve existir em config.parametros"
    )
    assert getattr(configuracao, "datas_termino_semestre", None) == {}
