"""Estrutura do backend conforme o C4 Nível 3 (BE-01)."""

import importlib

import pytest
from django.apps import apps

APPS_ANTIGOS = [
    "apps.core",
    "apps.status",
    "apps.avaliacoes",
    "apps.usuarios",
]


@pytest.mark.parametrize("app", APPS_ANTIGOS)
def test_app_antigo_foi_retirado(app):
    assert not apps.is_installed(app)


def test_leitor_e_modulo_do_app_cardapio():
    leitor = importlib.import_module("apps.cardapio.leitor")
    assert leitor.__name__ == "apps.cardapio.leitor"
