import os

import pytest
from django.db import connection

from apps.cardapio.models import Marcador


def test_configuracao_mysql_explicita(carregar_settings):
    banco = carregar_settings(
        DB_ENGINE="mysql",
        DB_PASSWORD="senha-apenas-de-teste",
    ).DATABASES["default"]

    assert banco["ENGINE"] == "django.db.backends.mysql"
    assert banco["OPTIONS"]["charset"] == "utf8mb4"
    assert banco["OPTIONS"]["isolation_level"] == "read committed"
    assert banco["TEST"]["CHARSET"] == "utf8mb4"
    assert banco["TEST"]["COLLATION"] == "utf8mb4_0900_ai_ci"


@pytest.mark.django_db
def test_preserva_acentos_e_caracteres_de_quatro_bytes():
    marcador = Marcador.objects.create(nome="Açúcar 🍚")

    marcador.refresh_from_db()

    assert marcador.nome == "Açúcar 🍚"


@pytest.mark.django_db
def test_mysql_real_usa_charset_e_isolamento_esperados():
    if os.environ.get("DB_ENGINE") == "mysql":
        assert connection.vendor == "mysql", (
            f"DB_ENGINE=mysql mas vendor={connection.vendor}"
        )
    elif connection.vendor != "mysql":
        pytest.skip("Verificação específica do job MySQL.")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT VERSION(), @@character_set_database, "
            "@@character_set_connection, @@collation_database, "
            "@@session.transaction_isolation"
        )
        (
            versao,
            charset_banco,
            charset_conexao,
            collation_banco,
            isolamento,
        ) = cursor.fetchone()

    assert versao.startswith("8.4.")
    assert charset_banco == "utf8mb4"
    assert charset_conexao == "utf8mb4"
    assert collation_banco == "utf8mb4_0900_ai_ci"
    assert isolamento == "READ-COMMITTED"


@pytest.mark.django_db
def test_job_mysql_roda_com_o_usuario_restrito():
    """#209: o job testes-mysql usa o usuário que o db/init/10-usuarios.sh
    cria em produção, e não o root. Uma migration que precise de um
    privilégio fora da lista falha no CI, e não só no deploy."""
    if os.environ.get("DB_ENGINE") != "mysql" or connection.vendor != "mysql":
        pytest.skip("Verificação específica do job MySQL.")

    with connection.cursor() as cursor:
        cursor.execute("SELECT CURRENT_USER()")
        (usuario,) = cursor.fetchone()
        cursor.execute("SHOW GRANTS")
        permissoes = [linha[0] for linha in cursor.fetchall()]

    assert not usuario.startswith("root@"), usuario
    assert not any("ALL PRIVILEGES" in p for p in permissoes), permissoes
    assert not any(" ON *.* " in p and "USAGE" not in p for p in permissoes), permissoes
