"""Estrutura do backend conforme o C4 Nível 3 (BE-01)."""

import pytest
from django.apps import apps
from django.core.management import call_command

APPS_DO_C4 = ["cadastro", "cardapio", "avaliacao", "fila", "gamificacao"]

# Apps do MVP antigo que saíram. O "cardapio" também era do MVP, mas o nome
# foi reaproveitado pelo app novo, por isso não está nesta lista.
APPS_ANTIGOS = ["core", "status", "avaliacoes", "usuarios"]


def test_manage_py_check_passa_sem_erros():
    # Mesmo critério do `python manage.py check` da issue, agora dentro da suíte
    # (e portanto também no CI da BE-02).
    call_command("check")


@pytest.mark.parametrize("nome", APPS_ANTIGOS)
def test_app_antigo_nao_volta(nome):
    with pytest.raises(LookupError):
        apps.get_app_config(nome)


def test_so_os_apps_do_c4_estao_instalados_alem_do_django_e_do_drf():
    do_projeto = sorted(
        config.label for config in apps.get_app_configs() if config.name.startswith("apps.")
    )
    assert do_projeto == sorted(APPS_DO_C4)
