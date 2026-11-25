"""Parâmetros da fila definidos no Anexo A e no Nível 4 da Fila."""

import pytest

from config import parametros


@pytest.mark.parametrize(
    ("atributo", "esperado"),
    [
        ("primeira_pergunta_min", 15),
        ("repeticao_min", 10),
        ("expiracao_min", 60),
        ("ponto_medio_ate5_min", 2.5),
        ("ponto_medio5a10_min", 7.5),
        ("faixa_minutos", 15),
        ("janela_semanas", 4),
        ("min_dias_distintos", 3),
        ("cortes", (25, 50, 75)),
        ("min_tempos_espera", 3),
        ("min_dias_espera", 2),
        ("retencao_semanas", 4),
    ],
)
def test_parametros_da_fila_correspondem_ao_anexo_a(atributo, esperado):
    configuracao = getattr(parametros, "ParametrosFilaConfig", None)

    assert configuracao is not None, (
        "ParametrosFilaConfig deve existir em config.parametros"
    )
    assert getattr(configuracao, atributo, None) == esperado
