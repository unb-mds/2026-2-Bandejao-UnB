import importlib

from django.apps import apps


def test_app_avaliacao_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("avaliacao")
    assert config.name == "apps.avaliacao"

    urls = importlib.import_module("apps.avaliacao.urls")
    assert isinstance(urls.urlpatterns, list)
