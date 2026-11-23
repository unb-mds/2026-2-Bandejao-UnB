"""Job testes-mysql com o usuário restrito do banco (#209, pendência da BD-05).

O job roda o `db/init/10-usuarios.sh` contra o MySQL do serviço, como na
primeira subida da VM, e passa a usar o usuário da aplicação, com os mesmos
privilégios de produção. O teste que confere a conexão de verdade está em
`test_banco_ci.py` e só roda no job MySQL; este lê o workflow.
"""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOW = RAIZ / ".github" / "workflows" / "backend-ci.yml"


def job_mysql():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["testes-mysql"]


def passos():
    return job_mysql()["steps"]


def indice(trecho):
    for posicao, passo in enumerate(passos()):
        if trecho in passo.get("run", ""):
            return posicao
    raise AssertionError(f"nenhum passo com {trecho!r}")


def test_servico_cria_o_usuario_da_aplicacao_como_na_vm():
    """Como o Compose: a imagem cria o MYSQL_USER com acesso total ao banco,
    e o script reduz os privilégios."""
    servico = job_mysql()["services"]["mysql"]["env"]

    assert servico["MYSQL_USER"] == job_mysql()["env"]["DB_USER"]
    assert servico["MYSQL_PASSWORD"] == job_mysql()["env"]["DB_PASSWORD"]
    assert servico["MYSQL_DATABASE"] == job_mysql()["env"]["DB_NAME"]


def test_django_conecta_com_o_usuario_restrito():
    assert job_mysql()["env"]["DB_USER"] != "root"


def test_script_de_usuarios_roda_antes_de_qualquer_manage_py():
    script = indice("10-usuarios.sh")
    primeiro_manage = min(
        posicao
        for posicao, passo in enumerate(passos())
        if "manage.py" in passo.get("run", "")
    )

    assert script < primeiro_manage


def test_permissoes_sao_conferidas_antes_dos_testes():
    conferencia = indice("SHOW GRANTS")

    assert "ALL PRIVILEGES" in passos()[conferencia]["run"]
    assert conferencia < indice("manage.py migrate")


def test_banco_de_teste_recebe_os_mesmos_privilegios_do_banco_da_aplicacao():
    """O pytest-django cria o test_<DB_NAME>. O CI dá a ele os privilégios
    que o script deu ao banco da aplicação, copiados do SHOW GRANTS, e não
    uma lista própria, que poderia ser maior que a de produção."""
    run = passos()[indice("test_")]["run"]

    assert "SHOW GRANTS" in run
    assert "test_" in run
    assert "ALL PRIVILEGES" not in run.replace('grep -q "ALL PRIVILEGES"', "")
