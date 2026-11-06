import importlib

from django.apps import apps


def test_app_gamificacao_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("gamificacao")
    assert config.name == "apps.gamificacao"

    urls = importlib.import_module("apps.gamificacao.urls")
    assert isinstance(urls.urlpatterns, list)
