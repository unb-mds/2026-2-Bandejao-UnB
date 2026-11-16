"""Estrutura do backend conforme o C4 Nível 3 (BE-01)."""

import io

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


@pytest.mark.django_db
def test_models_e_migrations_estao_sincronizados():
    # O banco de teste nasce das migrations, não dos models. Uma constraint
    # mudada só no models.py deixaria a suíte verde e o banco sem a regra (#110).
    # O django_db é porque o makemigrations confere o histórico no banco.
    saida = io.StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=saida)
    except SystemExit:
        faltando = saida.getvalue()
    else:
        return
    # Fora do except e sem pytrace, para a falha não vir com o traceback do
    # makemigrations na frente da migration que falta.
    pytest.fail(
        "Model alterado sem a migration correspondente. "
        "Rode `python manage.py makemigrations` e commite o arquivo.\n" + faltando,
        pytrace=False,
    )


@pytest.mark.parametrize("nome", APPS_ANTIGOS)
def test_app_antigo_nao_volta(nome):
    with pytest.raises(LookupError):
        apps.get_app_config(nome)


def test_so_os_apps_do_c4_estao_instalados_alem_do_django_e_do_drf():
    do_projeto = sorted(
        config.label
        for config in apps.get_app_configs()
        if config.name.startswith("apps.")
    )
    assert do_projeto == sorted(APPS_DO_C4)
