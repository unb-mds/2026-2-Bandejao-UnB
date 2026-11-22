"""Backup diário do banco de produção (BD-15, #183).

ADR 0008 (acesso restrito ao banco), ADR 0012 (VM) e Anexo A (7 dias de
guarda, para os dados de uma conta excluída também saírem dos backups,
RNF07.4). Os arquivos ficam em `deploy/backup/`:

- `backup-banco.sh`: mysqldump no container `db`, conferido, comprimido, com
  rotação por idade;
- `testar-restauracao.sh`: sobe um MySQL temporário, restaura a cópia e
  compara com a produção;
- `bandejao-backup`: o arquivo do `/etc/cron.d/`.

O MySQL e o cron de verdade só existem na VM; aqui os scripts rodam com um
`docker` e um `logger` falsos no PATH.
"""

import gzip
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PASTA = RAIZ / "deploy" / "backup"
BACKUP = PASTA / "backup-banco.sh"
RESTAURACAO = PASTA / "testar-restauracao.sh"
CRONTAB = PASTA / "bandejao-backup"
PASTA_NA_VM = "/home/azureuser/2026-2-Bandejao-UnB"

SH = shutil.which("sh")
precisa_de_sh = pytest.mark.skipif(SH is None, reason="sem sh no PATH")

DIA = 24 * 3600


# --- arquivos de deploy/backup ---------------------------------------------


def test_arquivos_de_backup_encontrados():
    assert BACKUP.is_file() and RESTAURACAO.is_file() and CRONTAB.is_file()


@pytest.mark.parametrize(
    "arquivo", [BACKUP, RESTAURACAO, CRONTAB], ids=lambda p: p.name
)
def test_terminam_com_quebra_de_linha_e_sem_crlf(arquivo):
    conteudo = arquivo.read_bytes()
    assert conteudo.endswith(b"\n")
    assert b"\r" not in conteudo


def test_nome_do_arquivo_vale_no_cron_d():
    """O cron ignora arquivos do `/etc/cron.d/` com ponto no nome."""
    assert re.fullmatch(r"[A-Za-z0-9_-]+", CRONTAB.name)


def tarefa_do_crontab():
    linhas = [
        linha
        for linha in CRONTAB.read_text(encoding="utf-8").splitlines()
        if linha.strip() and not linha.lstrip().startswith("#")
    ]
    tarefas = [linha for linha in linhas if not re.match(r"^[A-Z_]+=", linha)]
    assert len(tarefas) == 1, tarefas
    return tarefas[0]


def test_cron_roda_uma_vez_por_dia_como_azureuser_com_log():
    campos = tarefa_do_crontab().split(None, 6)
    minuto, hora, dia, mes, semana, usuario, comando = campos
    assert (dia, mes, semana) == ("*", "*", "*")
    assert minuto.isdigit() and hora.isdigit()  # uma execução por dia
    assert usuario == "azureuser"  # nunca root: a pasta do backup é dele
    assert comando.startswith(f"sh {PASTA_NA_VM}/deploy/backup/backup-banco.sh")
    assert ">> /var/log/bandejao/backup-banco.log 2>&1" in comando
    assert "sudo" not in comando


def test_cron_roda_depois_da_retencao_da_fila():
    """O backup sai depois do `desvincular_registros_fila` (BD-07), para a
    cópia já vir sem os vínculos de mais de 4 semanas."""
    minuto, hora = tarefa_do_crontab().split()[:2]
    retencao = re.search(
        r"^(\d+) (\d+) \* \* \* azureuser .*desvincular_registros_fila",
        (RAIZ / "deploy" / "cron" / "bandejao").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert retencao, "a retenção da fila saiu do cron"
    assert (int(hora), int(minuto)) > (int(retencao[2]), int(retencao[1]))


def test_path_do_cron_inclui_usr_bin():
    caminho = re.search(
        r"^PATH=(.+)$", CRONTAB.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert caminho and "/usr/bin" in caminho.group(1).split(":")


@precisa_de_sh
@pytest.mark.parametrize("script", [BACKUP, RESTAURACAO], ids=lambda p: p.name)
def test_sintaxe_do_sh(script):
    resultado = subprocess.run(
        [SH, "-n", script.as_posix()], check=False, capture_output=True, text=True
    )
    assert resultado.returncode == 0, resultado.stderr


def test_scripts_nao_levam_senha_nem_usam_set_x():
    for script in (BACKUP, RESTAURACAO):
        texto = script.read_text(encoding="utf-8")
        assert "set -x" not in texto
        # A senha do root só existe dentro do container: nenhum valor literal.
        assert not re.search(r"MYSQL_ROOT_PASSWORD=\S*[A-Za-z0-9]{8,}", texto)


# --- backup-banco.sh com docker e logger falsos -----------------------------

DUMP_COMPLETO = (
    "-- MySQL dump 10.13\nCREATE TABLE `cadastro_usuario` (id int);\n"
    "INSERT INTO `cadastro_usuario` VALUES (1);\n"
    "-- Dump completed on 2026-11-21 03:45:00\n"
)

DOCKER_FALSO = """#!/bin/sh
{ pwd -W 2>/dev/null || pwd; } > "$SAIDA_DOCKER"
for arg in "$@"; do printf '%s\\n' "$arg" >> "$SAIDA_DOCKER"; done
cat > "$SAIDA_DOCKER.entrada"
if [ -n "${ERRO_DOCKER:-}" ]; then printf '%s\\n' "$ERRO_DOCKER" >&2; fi
printf '%s' "${DUMP_TEXTO:-}"
exit "${FALHA_DOCKER:-0}"
"""

LOGGER_FALSO = """#!/bin/sh
printf '%s\\n' "$*" >> "$SAIDA_LOGGER"
"""


@pytest.fixture
def ambiente(tmp_path):
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    for nome, conteudo in (("docker", DOCKER_FALSO), ("logger", LOGGER_FALSO)):
        arquivo = bin_falso / nome
        arquivo.write_text(conteudo, encoding="utf-8", newline="\n")
        arquivo.chmod(0o755)
    backups = tmp_path / "backups"
    backups.mkdir()
    backups.chmod(0o755)  # o script tem que apertar para 700
    return {
        "bin": bin_falso,
        "backups": backups,
        "docker": tmp_path / "docker.txt",
        "logger": tmp_path / "logger.txt",
    }


@pytest.fixture
def rodar(ambiente):
    def rodar(dump=DUMP_COMPLETO, falha=None, erro=None, entrada="", **extra):
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("BANDEJAO_")
            and k not in ("FALHA_DOCKER", "ERRO_DOCKER", "DUMP_TEXTO")
        }
        env.update(
            PATH=str(ambiente["bin"]) + os.pathsep + os.environ["PATH"],
            SAIDA_DOCKER=ambiente["docker"].as_posix(),
            SAIDA_LOGGER=ambiente["logger"].as_posix(),
            BANDEJAO_BACKUPS=ambiente["backups"].as_posix(),
            DUMP_TEXTO=dump,
        )
        if falha is not None:
            env["FALHA_DOCKER"] = str(falha)
        if erro is not None:
            env["ERRO_DOCKER"] = erro
        env.update(extra)
        resultado = subprocess.run(
            [SH, BACKUP.as_posix()],
            check=False,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            input=entrada,
        )
        resultado.docker = ler_linhas(ambiente["docker"])
        resultado.entrada_do_docker = (
            Path(str(ambiente["docker"]) + ".entrada").read_text(encoding="utf-8")
            if Path(str(ambiente["docker"]) + ".entrada").exists()
            else None
        )
        resultado.logger = ler_linhas(ambiente["logger"]) or []
        return resultado

    return rodar


def ler_linhas(arquivo):
    return (
        arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else None
    )


def copias(ambiente):
    return sorted(ambiente["backups"].glob("bandejao-*.sql.gz"))


def criar_copia(ambiente, nome, idade_s):
    arquivo = ambiente["backups"] / nome
    arquivo.write_bytes(gzip.compress(b"-- Dump completed\n"))
    agora = time.time()
    os.utime(arquivo, (agora - idade_s, agora - idade_s))
    return arquivo


@precisa_de_sh
def test_backup_guarda_dump_comprimido_e_conferido(rodar, ambiente):
    resultado = rodar()
    assert resultado.returncode == 0, resultado.stderr
    [copia] = copias(ambiente)
    assert re.fullmatch(r"bandejao-\d{8}T\d{6}Z\.sql\.gz", copia.name)
    assert gzip.decompress(copia.read_bytes()).decode("utf-8") == DUMP_COMPLETO
    assert "ok:" in resultado.stdout and copia.name in resultado.stdout


@precisa_de_sh
def test_backup_so_o_dono_le_o_arquivo_e_a_pasta(rodar, ambiente):
    rodar()
    [copia] = copias(ambiente)
    assert copia.stat().st_mode & 0o777 == 0o600
    assert ambiente["backups"].stat().st_mode & 0o777 == 0o700


@precisa_de_sh
def test_backup_chama_o_mysqldump_no_container_db_sem_levar_a_senha(rodar):
    resultado = rodar()
    pasta, *argumentos = resultado.docker
    assert Path(pasta).name == RAIZ.name  # roda da pasta do repositório
    assert argumentos[:5] == ["compose", "exec", "-T", "db", "sh"] or (
        "compose" in argumentos and "exec" in argumentos and "db" in argumentos
    )
    texto = "\n".join(argumentos)
    for opcao in ("--single-transaction", "--routines", "--triggers", "utf8mb4"):
        assert opcao in texto
    # A senha é lida do ambiente do container, dentro do sh -c.
    assert '"$MYSQL_ROOT_PASSWORD"' in texto
    assert argumentos[-2:] == ["sh", "bandejao"]


@precisa_de_sh
def test_docker_nao_le_o_teclado_do_terminal(rodar):
    """Sem isso, rodar o script à mão num terminal travava em silêncio: o
    `docker compose exec -T` ficava esperando entrada, dentro do `timeout`."""
    resultado = rodar(entrada="digitado no terminal")
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.entrada_do_docker == ""


@precisa_de_sh
def test_backup_nao_deixa_temporarios(rodar, ambiente):
    rodar()
    assert [
        p.name for p in ambiente["backups"].iterdir() if p.name.startswith(".bandejao-")
    ] == []


@precisa_de_sh
def test_dump_incompleto_nao_vira_backup(rodar, ambiente):
    resultado = rodar(dump="-- MySQL dump\nCREATE TABLE x (id int);\n")
    assert resultado.returncode == 1
    assert copias(ambiente) == []
    assert [
        p for p in ambiente["backups"].iterdir() if p.name.startswith(".bandejao-")
    ] == []
    assert any("incompleto" in linha for linha in resultado.logger)


@precisa_de_sh
def test_dump_vazio_nao_vira_backup(rodar, ambiente):
    resultado = rodar(dump="")
    assert resultado.returncode == 1
    assert copias(ambiente) == []


@precisa_de_sh
def test_falha_do_mysqldump_sai_com_1_e_avisa_o_syslog(rodar, ambiente):
    resultado = rodar(falha=2, erro="mysqldump: Got error: 1045: Access denied")
    assert resultado.returncode == 1
    assert copias(ambiente) == []
    erros = [linha for linha in resultado.logger if "user.err" in linha]
    assert erros and "status 2" in erros[0] and "bandejao-backup" in erros[0]
    assert "Access denied" in erros[0]


@precisa_de_sh
def test_aviso_da_senha_na_linha_de_comando_nao_entra_no_log(rodar):
    resultado = rodar(
        falha=1,
        erro="mysqldump: [Warning] Using a password on the command line interface can be insecure.",
    )
    assert resultado.returncode == 1
    assert not any("Using a password" in linha for linha in resultado.logger)


@precisa_de_sh
def test_rotacao_apaga_o_que_passou_de_7_dias_e_guarda_o_resto(rodar, ambiente):
    velha = criar_copia(ambiente, "bandejao-20261110T064500Z.sql.gz", 10 * DIA)
    de_7_dias = criar_copia(ambiente, "bandejao-20261114T064500Z.sql.gz", 7 * DIA + 5)
    # A cópia de uma semana atrás chega ao próximo cron com 6 dias e 23 h
    # (menos uns segundos): tem que sair, senão a pasta teria 8 cópias.
    da_semana_passada = criar_copia(
        ambiente, "bandejao-20261115T064500Z.sql.gz", 6 * DIA + 23 * 3600 + 3590
    )
    de_6_dias = criar_copia(
        ambiente, "bandejao-20261115T074500Z.sql.gz", 6 * DIA + 21 * 3600
    )
    recente = criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = rodar()
    assert resultado.returncode == 0, resultado.stderr
    assert not velha.exists()
    assert not de_7_dias.exists()
    assert not da_semana_passada.exists()
    assert de_6_dias.exists() and recente.exists()
    # Com um backup por dia, nunca passa de 7 cópias (6 antigas + a de hoje).
    assert len(copias(ambiente)) == 3


@precisa_de_sh
def test_rotacao_roda_mesmo_se_o_dump_falhar(rodar, ambiente):
    """RNF07.4: o prazo de 7 dias vale mais que ter uma cópia."""
    velha = criar_copia(ambiente, "bandejao-20261101T064500Z.sql.gz", 20 * DIA)
    resultado = rodar(falha=1)
    assert resultado.returncode == 1
    assert not velha.exists()


@precisa_de_sh
def test_rotacao_so_mexe_nos_arquivos_de_backup(rodar, ambiente):
    outro = ambiente["backups"] / "anotacoes.txt"
    outro.write_text("não apagar", encoding="utf-8")
    os.utime(outro, (time.time() - 30 * DIA,) * 2)
    rodar()
    assert outro.exists()


@precisa_de_sh
def test_retencao_configuravel(rodar, ambiente):
    de_3_dias = criar_copia(ambiente, "bandejao-20261118T064500Z.sql.gz", 3 * DIA)
    de_1_dia = criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    rodar(BANDEJAO_RETENCAO_DIAS="2")
    assert not de_3_dias.exists() and de_1_dia.exists()


@precisa_de_sh
@pytest.mark.parametrize("valor", ["0", "-1", "sete", "7d"])
def test_retencao_invalida_sai_com_2_sem_apagar_nada(rodar, ambiente, valor):
    velha = criar_copia(ambiente, "bandejao-20261101T064500Z.sql.gz", 20 * DIA)
    resultado = rodar(BANDEJAO_RETENCAO_DIAS=valor)
    assert resultado.returncode == 2
    assert resultado.docker is None
    assert velha.exists()


@precisa_de_sh
@pytest.mark.parametrize("banco", ["bandejao; DROP", "a b", "x'y"])
def test_nome_de_banco_invalido_nao_chega_ao_docker(rodar, banco):
    resultado = rodar(BANDEJAO_BANCO=banco)
    assert resultado.returncode == 2
    assert resultado.docker is None


@precisa_de_sh
def test_pasta_de_backup_inexistente_explica_como_criar(rodar, ambiente):
    resultado = rodar(BANDEJAO_BACKUPS=(ambiente["backups"] / "nao-existe").as_posix())
    assert resultado.returncode == 1
    assert "install -d -m 700" in resultado.stderr
    assert resultado.docker is None


@precisa_de_sh
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="precisa de usuário comum no Linux"
)
def test_pasta_sem_escrita_avisa_do_sudo(rodar, ambiente):
    ambiente["backups"].chmod(0o500)
    try:
        resultado = rodar()
    finally:
        ambiente["backups"].chmod(0o700)
    assert resultado.returncode == 1
    assert "sem permissão de escrita" in resultado.stderr
    assert resultado.docker is None


@precisa_de_sh
@pytest.mark.skipif(shutil.which("flock") is None, reason="sem flock no PATH")
def test_segundo_backup_ao_mesmo_tempo_e_pulado(rodar, ambiente):
    import fcntl

    trava = ambiente["backups"] / ".trava"
    with open(trava, "a") as aberto:
        fcntl.flock(aberto, fcntl.LOCK_EX | fcntl.LOCK_NB)
        resultado = rodar()
    assert resultado.returncode == 75
    assert resultado.docker is None
    assert copias(ambiente) == []


@precisa_de_sh
def test_cada_backup_tem_nome_proprio(rodar, ambiente):
    rodar()
    time.sleep(1.1)
    rodar()
    assert len(copias(ambiente)) == 2


# --- testar-restauracao.sh com docker falso ---------------------------------

DOCKER_RESTAURACAO = """#!/bin/sh
printf '%s\\n' "$*" >> "$SAIDA_DOCKER"
case "$1" in
    rm) exit 0 ;;
    run) exit "${FALHA_RUN:-0}" ;;
    logs) echo "MySQL init process done. Ready for start up."; exit 0 ;;
    exec)
        # `exec -i <nome> mysql ...` (restauração): lê o dump da entrada.
        case "$*" in
            *mysqladmin*) exit 0 ;;
            *"-i "*) cat > "$SAIDA_DOCKER.dump"; exit "${FALHA_RESTAURAR:-0}" ;;
            *django_migrations*) echo "${MIGRACOES:-41}"; exit 0 ;;
            *"COUNT(*) FROM information_schema"*) echo "${TABELAS_TEMP:-30}"; exit 0 ;;
            *"SELECT table_name"*) echo cadastro_usuario; exit 0 ;;
            *'COUNT(*) FROM `'*) echo "${LINHAS:-3}"; exit 0 ;;
            *) exit 0 ;;
        esac ;;
    compose) echo "${TABELAS_PROD:-30}"; exit 0 ;;
esac
exit 0
"""


@pytest.fixture
def restaurar(ambiente):
    (ambiente["bin"] / "docker").write_text(
        DOCKER_RESTAURACAO, encoding="utf-8", newline="\n"
    )

    def restaurar(*argumentos, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("BANDEJAO_")}
        env.update(
            PATH=str(ambiente["bin"]) + os.pathsep + os.environ["PATH"],
            SAIDA_DOCKER=ambiente["docker"].as_posix(),
            BANDEJAO_BACKUPS=ambiente["backups"].as_posix(),
            BANDEJAO_ESPERA_TESTE="2",
        )
        env.update(extra)
        resultado = subprocess.run(
            [SH, RESTAURACAO.as_posix(), *argumentos],
            check=False,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        resultado.docker = ler_linhas(ambiente["docker"]) or []
        return resultado

    return restaurar


@precisa_de_sh
def test_restauracao_confere_a_copia_mais_recente(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261119T064500Z.sql.gz", 2 * DIA)
    nova = ambiente["backups"] / "bandejao-20261120T064500Z.sql.gz"
    nova.write_bytes(gzip.compress(DUMP_COMPLETO.encode()))
    resultado = restaurar()
    assert resultado.returncode == 0, resultado.stderr
    assert "OK: a restauração de bandejao-20261120T064500Z.sql.gz" in resultado.stdout
    restaurado = Path(str(ambiente["docker"]) + ".dump").read_text(encoding="utf-8")
    assert restaurado == DUMP_COMPLETO


@precisa_de_sh
def test_restauracao_mostra_a_contagem_exata_de_linhas(restaurar, ambiente):
    """O `table_rows` do information_schema é uma estimativa (0 logo depois de
    restaurar); a lista tem que vir de COUNT(*)."""
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(LINHAS="7")
    assert resultado.returncode == 0, resultado.stderr
    assert "  cadastro_usuario\t7" in resultado.stdout
    assert "table_rows" not in RESTAURACAO.read_text(encoding="utf-8").lower()


@precisa_de_sh
def test_restauracao_sobe_container_sem_rede_e_o_remove(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar()
    chamadas = resultado.docker
    run = next(c for c in chamadas if c.startswith("run "))
    assert "--network none" in run and "--rm" in run and "mysql:8.4" in run
    # Senha aleatória: não é nenhuma das senhas do .env, e muda a cada vez.
    assert "MYSQL_ROOT_PASSWORD=" in run
    assert chamadas[-1].startswith("rm -f bandejao-teste-restauracao")


@precisa_de_sh
def test_restauracao_com_numero_de_tabelas_diferente_falha(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(TABELAS_TEMP="29", TABELAS_PROD="30")
    assert resultado.returncode == 1
    assert "número de tabelas" in resultado.stderr
    assert "OK:" not in resultado.stdout


@precisa_de_sh
def test_restauracao_com_migracoes_vazias_falha(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(MIGRACOES="0")
    assert resultado.returncode == 1
    assert "django_migrations" in resultado.stderr


@precisa_de_sh
def test_restauracao_com_erro_no_mysql_falha_e_remove_o_container(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(FALHA_RESTAURAR="1")
    assert resultado.returncode == 1
    assert "erro ao restaurar" in resultado.stderr
    assert resultado.docker[-1].startswith("rm -f")


@precisa_de_sh
def test_restauracao_sem_backup_falha_sem_subir_container(restaurar):
    resultado = restaurar()
    assert resultado.returncode == 1
    assert "nenhum backup" in resultado.stderr
    assert resultado.docker == []


@precisa_de_sh
def test_restauracao_de_arquivo_corrompido_falha_sem_subir_container(
    restaurar, ambiente
):
    ruim = ambiente["backups"] / "bandejao-20261120T064500Z.sql.gz"
    ruim.write_bytes(b"isto nao e gzip")
    resultado = restaurar(ruim.as_posix())
    assert resultado.returncode == 1
    assert "gzip" in resultado.stderr
    assert resultado.docker == []


@precisa_de_sh
def test_restauracao_aceita_o_arquivo_como_argumento(restaurar, ambiente, tmp_path):
    fora = tmp_path / "outro.sql.gz"
    fora.write_bytes(gzip.compress(DUMP_COMPLETO.encode()))
    resultado = restaurar(fora.as_posix())
    assert resultado.returncode == 0, resultado.stderr
