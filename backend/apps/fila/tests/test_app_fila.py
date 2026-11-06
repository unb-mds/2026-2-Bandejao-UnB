import importlib

from django.apps import apps


def test_app_fila_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("fila")
    assert config.name == "apps.fila"

    urls = importlib.import_module("apps.fila.urls")
    assert isinstance(urls.urlpatterns, list)
