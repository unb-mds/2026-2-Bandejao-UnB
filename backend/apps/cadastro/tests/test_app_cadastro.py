import importlib

from django.apps import apps


def test_app_cadastro_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("cadastro")
    assert config.name == "apps.cadastro"

    urls = importlib.import_module("apps.cadastro.urls")
    assert isinstance(urls.urlpatterns, list)
