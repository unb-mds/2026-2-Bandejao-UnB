"""Parâmetros restantes do Anexo A, sem inventar valores indefinidos."""

from datetime import time, timedelta

import pytest
from django.conf import settings

from config import parametros


@pytest.mark.parametrize(
    ("classe", "atributo", "esperado"),
    [
        (
            "ParametrosLeitorConfig",
            "intervalo_verificacao",
            timedelta(hours=3),
        ),
        ("ParametrosLeitorConfig", "dia_alerta_nao_publicado", 0),
        ("ParametrosLeitorConfig", "horario_alerta_nao_publicado", time(12, 0)),
        ("ParametrosBackupConfig", "retencao", timedelta(days=7)),
        ("ParametrosBackupConfig", "intervalo", timedelta(days=1)),
        (
            "ParametrosLocalizacaoConfig",
            "tempo_nova_deteccao",
            timedelta(minutes=30),
        ),
        (
            "ParametrosLocalizacaoConfig",
            "tempo_limite_leitura",
            timedelta(seconds=5),
        ),
        ("ParametrosLocalizacaoConfig", "precisao_minima_metros", None),
        ("ParametrosLocalizacaoConfig", "idade_maxima_posicao", None),
    ],
)
def test_parametros_complementares_do_anexo_a(classe, atributo, esperado):
    configuracao = getattr(parametros, classe, None)

    assert configuracao is not None, f"{classe} deve existir em config.parametros"
    assert hasattr(configuracao, atributo), f"{classe}.{atributo} deve existir"
    assert getattr(configuracao, atributo) == esperado


def test_url_da_pagina_do_cardapio_definida_no_settings():
    assert getattr(settings, "URL_PAGINA_CARDAPIO", None) == (
        "https://ru.unb.br/cardapio-refeitorio/"
    )


def test_parametros_do_leitor_expoem_url_do_settings():
    configuracao = getattr(parametros, "ParametrosLeitorConfig", None)

    assert configuracao is not None, (
        "ParametrosLeitorConfig deve existir em config.parametros"
    )
    assert hasattr(settings, "URL_PAGINA_CARDAPIO")
    assert getattr(configuracao, "url_pagina", None) == settings.URL_PAGINA_CARDAPIO
