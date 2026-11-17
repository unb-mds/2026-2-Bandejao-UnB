"""Horários do Anexo A, compartilhados entre os componentes do backend."""

from datetime import time

import pytest

from config import parametros


@pytest.mark.parametrize(
    ("atributo", "esperado"),
    [
        ("horario_cafe", (time(7, 0), time(9, 30))),
        ("horario_almoco", (time(11, 0), time(14, 30))),
        ("horario_jantar", (time(17, 0), time(19, 30))),
    ],
)
def test_horarios_de_refeicao_correspondem_ao_anexo_a(atributo, esperado):
    configuracao = getattr(parametros, "HorariosRefeicaoConfig", None)

    assert configuracao is not None, (
        "HorariosRefeicaoConfig deve existir em config.parametros"
    )
    assert getattr(configuracao, atributo, None) == esperado
