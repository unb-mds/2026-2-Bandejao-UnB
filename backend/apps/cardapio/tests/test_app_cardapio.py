import importlib

from django.apps import apps


def test_app_cardapio_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("cardapio")
    assert config.name == "apps.cardapio"

    urls = importlib.import_module("apps.cardapio.urls")
    assert isinstance(urls.urlpatterns, list)
