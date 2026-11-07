import importlib

from django.apps import apps

from config import urls as urls_do_projeto


def test_app_cardapio_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("cardapio")
    assert config.name == "apps.cardapio"

    urls = importlib.import_module("apps.cardapio.urls")
    assert isinstance(urls.urlpatterns, list)


def test_app_cardapio_incluido_em_api_no_config_urls():
    incluidos = [
        padrao
        for padrao in urls_do_projeto.urlpatterns
        if getattr(padrao, "app_name", None) == "cardapio"
    ]
    assert len(incluidos) == 1
    assert str(incluidos[0].pattern) == "api/"


def test_modulo_leitor_do_cardapio_existe():
    # ADR 0003: o Leitor de Cardápio é um módulo dentro do app Cardápio.
    leitor = importlib.import_module("apps.cardapio.leitor")
    assert leitor.__name__ == "apps.cardapio.leitor"
