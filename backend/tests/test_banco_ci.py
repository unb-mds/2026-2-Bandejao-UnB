import os
import re

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


def so_no_job_mysql():
    if os.environ.get("DB_ENGINE") != "mysql":
        pytest.skip("Verificação específica do job MySQL.")


@pytest.mark.django_db
def test_privilegios_de_banco_com_curingas_escapados():
    r"""#250: no GRANT de banco, `_` e `%` são curingas. Todo `_` ou `%` no
    nome de um banco do SHOW GRANTS precisa vir escapado (`bandejao\_ci`)."""
    so_no_job_mysql()

    with connection.cursor() as cursor:
        cursor.execute("SHOW GRANTS")
        permissoes = [linha[0] for linha in cursor.fetchall()]

    bancos = [
        nome
        for permissao in permissoes
        for nome in re.findall(r" ON `((?:[^`]|``)+)`\.\*", permissao)
    ]
    assert bancos, permissoes
    for nome in bancos:
        assert not re.search(r"(?<!\\)[_%]", nome), permissoes


def test_usuario_da_aplicacao_nao_cria_banco_que_casa_com_o_curinga():
    """#250: com o `_` sem escape, o GRANT em `bandejao_ci` valeria para
    `bandejaoXci`, e o CREATE passaria. Conexão própria, fora do banco de
    teste do pytest-django: o CREATE DATABASE faz commit implícito."""
    so_no_job_mysql()
    import MySQLdb

    nome_da_aplicacao = os.environ["DB_NAME"]
    assert "_" in nome_da_aplicacao, "o teste precisa de um nome com `_`"
    parecido = nome_da_aplicacao.replace("_", "X")

    conexao = MySQLdb.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    try:
        cursor = conexao.cursor()
        with pytest.raises(MySQLdb.OperationalError) as erro:
            cursor.execute(f"CREATE DATABASE `{parecido}`")
        assert erro.value.args[0] == 1044, erro.value.args
    finally:
        # Se o teste falhar, o banco criado não fica para trás.
        try:
            conexao.cursor().execute(f"DROP DATABASE IF EXISTS `{parecido}`")
        except MySQLdb.OperationalError:
            pass
        conexao.close()
