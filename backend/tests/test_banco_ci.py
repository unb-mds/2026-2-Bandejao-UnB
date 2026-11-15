import runpy
from pathlib import Path

import pytest
from django.db import connection

from apps.cardapio.models import Marcador


def test_configuracao_mysql_explicita(monkeypatch):
    monkeypatch.setenv("DB_ENGINE", "mysql")
    monkeypatch.setenv("DB_PASSWORD", "senha-apenas-de-teste")

    arquivo = Path(__file__).resolve().parents[1] / "config" / "settings.py"
    configuracao = runpy.run_path(str(arquivo))
    banco = configuracao["DATABASES"]["default"]

    assert banco["ENGINE"] == "django.db.backends.mysql"
    assert banco["OPTIONS"]["charset"] == "utf8mb4"
    assert banco["OPTIONS"].get("isolation_level") == "read committed"
    assert banco.get("TEST", {}).get("CHARSET") == "utf8mb4"


@pytest.mark.django_db
def test_preserva_acentos_e_caracteres_de_quatro_bytes():
    marcador = Marcador.objects.create(nome="Açúcar 🍚")

    marcador.refresh_from_db()

    assert marcador.nome == "Açúcar 🍚"


@pytest.mark.django_db
def test_mysql_real_usa_charset_e_isolamento_esperados():
    if connection.vendor != "mysql":
        pytest.skip("Verificação específica do job MySQL.")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT VERSION(), @@character_set_database, "
            "@@character_set_connection, @@session.transaction_isolation"
        )
        versao, charset_banco, charset_conexao, isolamento = cursor.fetchone()

    assert versao.startswith("8.")
    assert charset_banco == "utf8mb4"
    assert charset_conexao == "utf8mb4"
    assert isolamento == "READ-COMMITTED"