"""Duração da sessão exposta sem duplicar o valor do settings (BD-04)."""

from importlib import reload

from django.conf import settings
from django.test import override_settings

from config import parametros


def test_duracao_da_sessao_corresponde_ao_settings():
    configuracao = getattr(parametros, "ParametrosSessaoConfig", None)

    assert configuracao is not None, (
        "ParametrosSessaoConfig deve existir em config.parametros"
    )
    assert (
        getattr(configuracao, "duracao_segundos", None) == settings.SESSION_COOKIE_AGE
    )


def test_configuracao_le_duracao_personalizada_do_settings():
    try:
        with override_settings(SESSION_COOKIE_AGE=3600):
            reload(parametros)
            configuracao = getattr(parametros, "ParametrosSessaoConfig", None)

            assert configuracao is not None, (
                "ParametrosSessaoConfig deve existir em config.parametros"
            )
            assert getattr(configuracao, "duracao_segundos", None) == 3600
    finally:
        reload(parametros)
