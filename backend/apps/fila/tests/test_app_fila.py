import importlib

from django.apps import apps

from config import urls as urls_do_projeto


def test_app_fila_instalado_com_o_nome_do_c4_e_com_urls():
    config = apps.get_app_config("fila")
    assert config.name == "apps.fila"

    urls = importlib.import_module("apps.fila.urls")
    assert isinstance(urls.urlpatterns, list)


def test_app_fila_incluido_em_api_no_config_urls():
    incluidos = [
        padrao
        for padrao in urls_do_projeto.urlpatterns
        if getattr(padrao, "app_name", None) == "fila"
    ]
    assert len(incluidos) == 1
    assert str(incluidos[0].pattern) == "api/"
