"""Parâmetros do Anexo A já utilizados pelo cadastro e pelo login."""

from datetime import timedelta

import pytest

from config import parametros


@pytest.mark.parametrize(
    ("atributo", "esperado"),
    [
        ("primeiro_ano_matricula", 10),
        ("validade_confirmacao_email", timedelta(hours=24)),
        ("login_max_tentativas", 5),
        ("login_janela", timedelta(minutes=10)),
        ("login_bloqueio", timedelta(minutes=10)),
    ],
)
def test_parametros_do_cadastro_correspondem_ao_anexo_a(atributo, esperado):
    configuracao = getattr(parametros, "ParametrosCadastroConfig", None)

    assert configuracao is not None, (
        "ParametrosCadastroConfig deve existir em config.parametros"
    )
    assert getattr(configuracao, atributo, None) == esperado
