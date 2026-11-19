"""Arquivos do MySQL de produção em db/ (BD-05, #91).

O Compose monta `db/conf.d/` em `/etc/mysql/conf.d/` e `db/init/` em
`/docker-entrypoint-initdb.d/`. O MySQL de verdade só existe na VM; aqui o
`.cnf` é lido como texto, e o script de usuários roda com um `mysql` falso no
PATH, que só grava o SQL recebido.
"""

import configparser
import os
import re
import shutil
import subprocess
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


def test_privilegios_so_no_banco_da_aplicacao(script):
    """Nenhum GRANT global (*.*), que valeria para o banco mysql também."""
    assert "ON *.*" not in script


# --- O script rodando com um mysql falso -----------------------------------

SH = shutil.which("sh")
precisa_de_sh = pytest.mark.skipif(SH is None, reason="sem sh no PATH")

MYSQL_FALSO = """#!/bin/sh
cat >> "$SAIDA_SQL"
exit "${FALHA_MYSQL:-0}"
"""

AMBIENTE_DO_CONTAINER = {
    "MYSQL_ROOT_PASSWORD": "senha-root",
    "MYSQL_DATABASE": "bandejao",
    "MYSQL_USER": "app_bandejao",
    "DB_EQUIPE_USER": "equipe",
    "DB_EQUIPE_PASSWORD": "senha-equipe",
}


@pytest.fixture
def rodar(tmp_path):
    """Roda o script como na VM: `sh script` (`modo="executar"`) ou com
    `source` sob `set -e`, como a imagem do MySQL (`modo="source"`)."""
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    mysql = bin_falso / "mysql"
    mysql.write_text(MYSQL_FALSO, encoding="utf-8", newline="\n")
    mysql.chmod(0o755)
    saida = tmp_path / "saida.sql"

    def rodar(modo="executar", falha=False, **ambiente):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in AMBIENTE_DO_CONTAINER and k != "FALHA_MYSQL"
        }
        env.update(
            PATH=str(bin_falso) + os.pathsep + os.environ["PATH"],
            SAIDA_SQL=saida.as_posix(),
        )
        if falha:
            env["FALHA_MYSQL"] = "1"
        for nome, valor in {**AMBIENTE_DO_CONTAINER, **ambiente}.items():
            if valor is not None:
                env[nome] = valor

        caminho = SCRIPT_USUARIOS.as_posix()
        if modo == "executar":
            comando = [SH, caminho]
        else:
            comando = [SH, "-ec", '. "$0"; echo depois-do-script', caminho]
        resultado = subprocess.run(
            comando, env=env, capture_output=True, text=True, encoding="utf-8"
        )
        resultado.sql = saida.read_text(encoding="utf-8") if saida.exists() else ""
        return resultado

    return rodar


def privilegios(sql, destino):
    linha = re.search(rf"GRANT ([A-Z, ]+) ON .* TO {re.escape(destino)}", sql)
    assert linha, f"GRANT para {destino} não encontrado"
    return {p.strip() for p in linha.group(1).split(",")}


@precisa_de_sh
def test_aplicacao_perde_o_all_privileges_da_imagem(rodar):
    """A imagem do MySQL dá ALL no banco ao MYSQL_USER; o script reduz."""
    sql = rodar().sql

    assert "REVOKE IF EXISTS ALL PRIVILEGES ON `bandejao`.* FROM 'app_bandejao'" in sql


@precisa_de_sh
def test_aplicacao_so_tem_o_que_o_django_usa(rodar):
    # Dados e migrations (CREATE/ALTER/DROP/INDEX/REFERENCES das FKs).
    assert privilegios(rodar().sql, "'app_bandejao'") == {
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


@precisa_de_sh
def test_equipe_so_mexe_nos_dados(rodar):
    assert privilegios(rodar().sql, "'equipe_moderacao'") == {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
    }


@precisa_de_sh
def test_banco_com_sublinhado_tambem_perde_o_all(rodar):
    r"""A imagem dá o GRANT com o `_` escapado (`ru\_db`): o REVOKE só com o
    nome puro não casaria, e o ALL ficaria."""
    sql = rodar(MYSQL_DATABASE="ru_db").sql

    assert r"REVOKE IF EXISTS ALL PRIVILEGES ON `ru\_db`.* FROM" in sql
    assert "REVOKE IF EXISTS ALL PRIVILEGES ON `ru_db`.* FROM" in sql


@precisa_de_sh
def test_valores_com_aspas_e_barras_viram_texto_no_sql(rodar):
    """Aspas, barra invertida, $(...) e crase não fecham o texto nem rodam."""
    resultado = rodar(
        MYSQL_USER="app'x",
        DB_EQUIPE_USER="o'brien",
        DB_EQUIPE_PASSWORD=r"a'b\c$(id)`id`",
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "FROM 'app''x'@'%'" in resultado.sql
    assert "CREATE USER IF NOT EXISTS 'o''brien'@'%'" in resultado.sql
    assert r"IDENTIFIED BY 'a''b\\c$(id)`id`'" in resultado.sql


@precisa_de_sh
def test_cria_o_usuario_da_equipe_com_o_papel_padrao(rodar):
    sql = rodar().sql

    assert "GRANT 'equipe_moderacao' TO 'equipe'@'%'" in sql
    assert "SET DEFAULT ROLE 'equipe_moderacao' TO 'equipe'@'%'" in sql


@precisa_de_sh
def test_sem_usuario_da_equipe_avisa_e_segue(rodar):
    """Com source, a subida do banco continua; o aviso diz como corrigir."""
    resultado = rodar(modo="source", DB_EQUIPE_USER=None)

    assert resultado.returncode == 0, resultado.stderr
    assert "depois-do-script" in resultado.stdout
    assert "AVISO" in resultado.stderr
    assert "--force-recreate" in resultado.stderr
    assert "CREATE USER" not in resultado.sql


@precisa_de_sh
def test_rodado_a_mao_sai_com_erro_se_o_mysql_falhar(rodar):
    """Pelo comando do guia não há set -e: sem isto, o status seria 0."""
    resultado = rodar(falha=True)

    assert resultado.returncode != 0
    assert "ERRO" in resultado.stderr


@precisa_de_sh
def test_com_source_um_erro_para_a_subida(rodar):
    """Na imagem (source sob set -e), o erro para a primeira subida."""
    resultado = rodar(modo="source", falha=True)

    assert resultado.returncode != 0
    assert "depois-do-script" not in resultado.stdout
