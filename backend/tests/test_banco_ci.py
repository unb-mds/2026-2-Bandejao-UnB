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
