"""Arquivos do MySQL de produção em db/ (BD-05, #91).

O Compose monta `db/conf.d/` em `/etc/mysql/conf.d/` e `db/init/` em
`/docker-entrypoint-initdb.d/`. O MySQL de verdade só existe na VM e no job
MySQL do CI; aqui o teste confere o conteúdo dos arquivos, para que uma
mudança neles não passe sem ninguém ver.
"""

import configparser
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CONF_D = RAIZ / "db" / "conf.d"
INIT = RAIZ / "db" / "init"
SCRIPT_USUARIOS = INIT / "10-usuarios.sh"


@pytest.fixture(scope="module")
def cnf():
    arquivos = sorted(CONF_D.glob("*.cnf"))
    assert arquivos, "Nenhum .cnf em db/conf.d/"
    leitor = configparser.ConfigParser(allow_no_value=True)
    for arquivo in arquivos:
        leitor.read(arquivo, encoding="utf-8")
    return leitor


@pytest.fixture(scope="module")
def script():
    return SCRIPT_USUARIOS.read_text(encoding="utf-8")


def opcao(cnf, secao, nome):
    """O MySQL aceita `-` e `_` no nome da opção."""
    for variante in (nome, nome.replace("-", "_")):
        if cnf.has_option(secao, variante):
            return cnf.get(secao, variante)
    return None


def test_servidor_em_utf8mb4(cnf):
    assert opcao(cnf, "mysqld", "character-set-server") == "utf8mb4"
    # A mesma collation do banco de teste (settings.py, DATABASES TEST).
    assert opcao(cnf, "mysqld", "collation-server") == "utf8mb4_0900_ai_ci"


def test_servidor_em_read_committed(cnf):
    assert opcao(cnf, "mysqld", "transaction-isolation") == "READ-COMMITTED"


def test_cliente_do_container_em_utf8mb4(cnf):
    """O `mysql` da equipe (dentro do container) mostra os acentos certos."""
    assert opcao(cnf, "client", "default-character-set") == "utf8mb4"


def test_script_nao_tem_senha_escrita(script):
    """As senhas vêm do ambiente do container (.env e .env.db), nunca do Git."""
    assert not re.search(r"IDENTIFIED BY '[^$]", script)


def test_aplicacao_perde_o_all_privileges_da_imagem(script):
    """A imagem do MySQL dá ALL no banco ao MYSQL_USER; o script reduz."""
    assert re.search(r"REVOKE IF EXISTS ALL PRIVILEGES ON .* FROM", script)


def test_aplicacao_so_tem_o_que_o_django_usa(script):
    linha = re.search(r"GRANT ([A-Z, ]+) ON .* TO '\$\{?MYSQL_USER", script)
    assert linha, "GRANT do usuário da aplicação não encontrado"
    privilegios = {p.strip() for p in linha.group(1).split(",")}

    # Dados e migrations (CREATE/ALTER/DROP/INDEX/REFERENCES das FKs).
    assert privilegios == {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "ALTER",
        "DROP",
        "INDEX",
        "REFERENCES",
    }


def test_equipe_so_mexe_nos_dados(script):
    linha = re.search(r"GRANT ([A-Z, ]+) ON .* TO 'equipe_moderacao'", script)
    assert linha, "GRANT do papel da equipe não encontrado"
    privilegios = {p.strip() for p in linha.group(1).split(",")}

    assert privilegios == {"SELECT", "INSERT", "UPDATE", "DELETE"}


def test_privilegios_so_no_banco_da_aplicacao(script):
    """Nenhum GRANT global (*.*), que valeria para o banco mysql também."""
    assert "ON *.*" not in script
