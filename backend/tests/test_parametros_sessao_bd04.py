"""A configuração da sessão deve acompanhar os settings sem reload."""

from django.conf import settings
from django.test import override_settings

from config.parametros import ParametrosSessaoConfig


def test_duracao_da_sessao_corresponde_ao_settings():
    configuracao = ParametrosSessaoConfig()

    assert configuracao.duracao_segundos == settings.SESSION_COOKIE_AGE


def test_configuracao_acompanha_alteracao_e_restauracao_do_settings():
    configuracao = ParametrosSessaoConfig()
    duracao_original = settings.SESSION_COOKIE_AGE

    with override_settings(SESSION_COOKIE_AGE=3600):
        assert configuracao.duracao_segundos == 3600

    with override_settings(SESSION_COOKIE_AGE=7200):
        assert configuracao.duracao_segundos == 7200

    assert configuracao.duracao_segundos == duracao_original
