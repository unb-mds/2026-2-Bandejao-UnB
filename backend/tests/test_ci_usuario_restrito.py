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


def passo_chamado(comeco):
    """O passo pelo nome, e não pelo primeiro `run` que tenha um trecho."""
    for passo in passos():
        if passo.get("name", "").startswith(comeco):
            return passo
    raise AssertionError(f"nenhum passo chamado {comeco!r}")


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
    run = passo_chamado("Dar ao banco de teste")["run"]

    assert "SHOW GRANTS" in run
    # O GRANT usa os privilégios lidos do SHOW GRANTS, e não uma lista escrita
    # no workflow.
    assert "GRANT $privilegios ON" in run
    for privilegio in ("SELECT", "INSERT", "ALL PRIVILEGES"):
        assert f"GRANT {privilegio}" not in run


def test_nome_do_banco_de_teste_vai_escapado_no_grant():
    """No GRANT, o `_` é curinga: sem o escape, o privilégio valeria para
    qualquer banco que casasse com o padrão (testXbandejao_ci, por exemplo)."""
    run = passo_chamado("Dar ao banco de teste")["run"]

    assert "sed 's/_/\\\\_/g'" in run
    # As crases vêm escapadas dentro das aspas duplas do bash.
    assert "\\`$banco_de_teste\\`.*" in run


def test_conferencia_procura_o_nome_escapado_e_falha_sem_escape():
    """#250: o SHOW GRANTS certo mostra o banco com o `_` escapado. Um GRANT
    no nome sem escape (curinga) falha o passo, no usuário e no papel."""
    run = passo_chamado("Conferir as permissões")["run"]

    assert "sed 's/[_%]/\\\\&/g'" in run
    assert "equipe_moderacao" in run
    assert 'grep -qF "ON \\`$banco_escapado\\`.*"' in run
    assert 'grep -F "ON \\`$DB_NAME\\`.*"' in run


def test_grants_antigos_sem_escape_existem_antes_do_script():
    """Revisão do #298: como na VM antes da #250, o usuário e o papel já têm
    GRANTs no nome sem escape quando o script roda. A conferência depois do
    script prova que os REVOKEs tiram esses GRANTs num MySQL de verdade."""
    passo = passo_chamado("Dar os GRANTs antigos")
    run = passo["run"]

    assert "CREATE ROLE IF NOT EXISTS 'equipe_moderacao'" in run
    assert "ON \\`$DB_NAME\\`.* TO '$DB_USER'@'%'" in run
    assert "ON \\`$DB_NAME\\`.* TO 'equipe_moderacao'" in run
    assert passos().index(passo) < indice("10-usuarios.sh")


def test_copia_para_o_banco_de_teste_le_a_linha_do_nome_escapado():
    run = passo_chamado("Dar ao banco de teste")["run"]

    assert 'grep -F "ON \\`$banco_escapado\\`.*"' in run


def test_senha_de_root_so_nos_passos_que_usam_o_root():
    """O migrate e o pytest não recebem a senha de root."""
    job = job_mysql()
    senha = job["services"]["mysql"]["env"]["MYSQL_ROOT_PASSWORD"]

    assert "MYSQL_ROOT_PASSWORD" not in job["env"]
    passos_do_root = [p for p in passos() if "-uroot" in p.get("run", "")]
    assert passos_do_root
    for passo in passos_do_root:
        assert passo["env"]["MYSQL_PWD"] == senha, passo["name"]
    for passo in passos():
        if "manage.py" in passo.get("run", "") or "pytest" in passo.get("run", ""):
            assert "MYSQL_PWD" not in passo.get("env", {}), passo.get("name")
