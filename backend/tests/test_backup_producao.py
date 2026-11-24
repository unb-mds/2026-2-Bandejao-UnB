"""Backup diário do banco de produção (BD-15, #183).

ADR 0008 (acesso restrito ao banco), ADR 0012 (VM) e Anexo A (7 dias de
guarda, para os dados de uma conta excluída também saírem dos backups,
RNF07.4). Os arquivos ficam em `deploy/backup/`:

- `backup-banco.sh`: mysqldump no container `db`, conferido, comprimido, com
  rotação por idade e log próprio;
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
import signal
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

# `-p` (colado ou não à senha) e `--password`: a senha não pode ir como argumento.
SENHA_NA_LINHA = re.compile(r"(^|\s)-p\S*|--password")


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
    # Sem redireção, como as linhas do BD-07: quem grava o log é o script, que
    # testa a escrita e avisa o syslog. Com `>>` na linha, um log que não abre
    # faria o `sh` do cron falhar antes de o script rodar.
    assert ">" not in comando.split("backup-banco.sh", 1)[1]
    assert "sudo" not in comando


def test_cron_roda_depois_da_retencao_da_fila():
    """O backup sai depois do `desvincular_registros_fila` (BD-11, no cron do
    BD-07), para a cópia normalmente já vir sem os vínculos de mais de 4
    semanas."""
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
if [ -n "${SONO_DOCKER:-}" ]; then exec sleep "$SONO_DOCKER"; fi
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
    logs = tmp_path / "logs"
    return {
        "bin": bin_falso,
        "backups": backups,
        "logs": logs,
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
            BANDEJAO_LOGS=ambiente["logs"].as_posix(),
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
        # O script grava o próprio log: é nele que estão o resumo e os erros.
        resultado.log = ler_texto(ambiente["logs"] / "backup-banco.log")
        return resultado

    return rodar


def ler_linhas(arquivo):
    return (
        arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else None
    )


def ler_texto(arquivo):
    return arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""


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
    assert "ok:" in resultado.log and copia.name in resultado.log
    # Registrado também no syslog, para "rodou bem" e "nem rodou" não ficarem
    # iguais no journalctl.
    assert any("user.info" in linha and "ok:" in linha for linha in resultado.logger)


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
    assert argumentos[:4] == ["compose", "exec", "-T", "db"]
    # O `timeout` roda dentro do container, para o mysqldump morrer junto:
    # vem depois do `db` e antes do `sh -c`, com o limite de 30m.
    assert "timeout" in argumentos and "30m" in argumentos
    assert argumentos.index("db") < argumentos.index("timeout") < argumentos.index("sh")
    assert argumentos[argumentos.index("sh") + 1] == "-c"
    texto = "\n".join(argumentos)
    for opcao in ("--single-transaction", "--routines", "--triggers", "utf8mb4"):
        assert opcao in texto
    # A senha é lida do ambiente do container e vai ao mysqldump por MYSQL_PWD,
    # nunca como -p: assim não aparece no `ps`.
    assert 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD"' in texto
    assert not SENHA_NA_LINHA.search(texto)
    # A tabela de cache do limite de taxa (IP) fica fora do dump.
    assert '--ignore-table="$1.cache_bandejao"' in texto
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
    assert "incompleto" in resultado.log


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
    # Exatamente 7 dias (mais uns segundos): já passou do prazo.
    de_7_dias = criar_copia(ambiente, "bandejao-20261114T064500Z.sql.gz", 7 * DIA + 5)
    # A cópia de uma semana atrás chega ao próximo cron com 7 dias menos uns
    # segundos (aqui, 10 s): tem que sair, senão a pasta teria 8 cópias. A
    # folga de 2 h da rotação é o que garante isso com o horário do cron
    # variando.
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
    # Sobram as duas de menos de 7 dias menos 2 h e a de hoje.
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


GZIP_QUE_FALHA_NO_TESTE = """#!/bin/sh
for arg in "$@"; do
    if [ "$arg" = "-t" ]; then echo "gzip: arquivo corrompido" >&2; exit 1; fi
done
exec "$GZIP_REAL" "$@"
"""


@precisa_de_sh
def test_rotacao_so_apaga_arquivos_comuns_do_padrao_na_pasta(rodar, ambiente):
    """Sem `-maxdepth 1` e `-type f`, o `find` entraria em subpastas e
    apagaria diretórios; e o padrão é `bandejao-*.sql.gz`, não `.sql`."""
    antigo = 30 * DIA
    sub = ambiente["backups"] / "arquivo-morto"
    sub.mkdir()
    na_subpasta = sub / "bandejao-20261001T064500Z.sql.gz"
    na_subpasta.write_bytes(gzip.compress(b"x"))
    sem_gz = ambiente["backups"] / "bandejao-20261001T064500Z.sql"
    sem_gz.write_text("-- Dump completed\n", encoding="utf-8")
    diretorio = ambiente["backups"] / "bandejao-20261002T064500Z.sql.gz"
    diretorio.mkdir()
    for caminho in (na_subpasta, sem_gz, diretorio, sub):
        os.utime(caminho, (time.time() - antigo,) * 2)
    resultado = rodar()
    assert resultado.returncode == 0, resultado.stderr
    assert na_subpasta.exists() and sem_gz.exists() and diretorio.is_dir()


@precisa_de_sh
def test_gzip_que_falha_na_conferencia_nao_vira_backup(rodar, ambiente):
    gzip_real = shutil.which("gzip")
    falso = ambiente["bin"] / "gzip"
    falso.write_text(GZIP_QUE_FALHA_NO_TESTE, encoding="utf-8", newline="\n")
    falso.chmod(0o755)
    resultado = rodar(GZIP_REAL=gzip_real)
    assert resultado.returncode == 1
    assert copias(ambiente) == []
    assert "comprimir" in resultado.log


@precisa_de_sh
def test_linha_de_dump_completo_so_vale_na_ultima_linha(rodar, ambiente):
    dump = "-- Dump completed on x\nINSERT INTO t VALUES (1);\n-- cortado aqui\n"
    resultado = rodar(dump=dump)
    assert resultado.returncode == 1
    assert copias(ambiente) == []
    assert "incompleto" in resultado.log


@precisa_de_sh
@pytest.mark.parametrize(
    ("status", "texto"),
    [(124, "tempo esgotado"), (137, "KILL"), (127, "timeout")],
)
def test_status_do_timeout_tem_mensagem_propria(rodar, status, texto):
    resultado = rodar(falha=status)
    assert resultado.returncode == 1
    assert texto in resultado.log
    assert texto in resultado.stderr


@precisa_de_sh
def test_falha_que_deixa_a_pasta_sem_copia_avisa_com_crit(rodar, ambiente):
    criar_copia(ambiente, "bandejao-20261101T064500Z.sql.gz", 20 * DIA)
    resultado = rodar(falha=1)
    assert copias(ambiente) == []  # a rotação apagou a última
    crit = [linha for linha in resultado.logger if "user.crit" in linha]
    assert crit and "SEM NENHUMA CÓPIA" in crit[0] and "bandejao-backup" in crit[0]


@precisa_de_sh
def test_falha_com_a_copia_mais_nova_velha_demais_avisa_com_crit(rodar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 30 * 3600)
    resultado = rodar(falha=1)
    crit = [linha for linha in resultado.logger if "user.crit" in linha]
    assert crit and "mais de 26 h" in crit[0]


@precisa_de_sh
def test_falha_com_copia_de_ontem_nao_avisa_com_crit(rodar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 24 * 3600)
    resultado = rodar(falha=1)
    assert resultado.returncode == 1
    assert not any("user.crit" in linha for linha in resultado.logger)


@precisa_de_sh
def test_backup_que_deu_certo_nao_avisa_com_crit(rodar):
    resultado = rodar()
    assert not any("user.crit" in linha for linha in resultado.logger)


@precisa_de_sh
def test_tamanho_que_despenca_em_relacao_a_copia_anterior_avisa(rodar, ambiente):
    anterior = ambiente["backups"] / "bandejao-20261120T064500Z.sql.gz"
    anterior.write_bytes(os.urandom(5000))  # incompressível: tamanho fixo
    os.utime(anterior, (time.time() - DIA,) * 2)
    resultado = rodar()
    assert resultado.returncode == 0, resultado.stderr
    avisos = [linha for linha in resultado.logger if "user.warning" in linha]
    assert avisos and "menos da metade" in avisos[0]


def tamanho_do_backup_novo(rodar, ambiente):
    """Roda uma vez, mede a cópia e a apaga: o tamanho (com o nome do tmp no
    cabeçalho do gzip) é o mesmo nas execuções seguintes."""
    rodar()
    [copia] = copias(ambiente)
    tamanho = copia.stat().st_size
    copia.unlink()
    return tamanho


@precisa_de_sh
@pytest.mark.parametrize(
    ("extra", "avisa"),
    [(1, True), (0, False)],
    ids=["logo-abaixo-da-metade", "na-metade"],
)
def test_limite_exato_de_metade_do_tamanho_da_copia_anterior(
    rodar, ambiente, extra, avisa
):
    novo = tamanho_do_backup_novo(rodar, ambiente)
    anterior = ambiente["backups"] / "bandejao-20261120T064500Z.sql.gz"
    anterior.write_bytes(os.urandom(2 * novo + extra))
    os.utime(anterior, (time.time() - DIA,) * 2)
    resultado = rodar()
    assert resultado.returncode == 0, resultado.stderr
    assert any("menos da metade" in linha for linha in resultado.logger) is avisa


@precisa_de_sh
def test_tmp_recente_fica_e_o_de_mais_de_um_dia_sai(rodar, ambiente):
    recente = ambiente["backups"] / ".bandejao-20261123T060000Z.tmp"
    recente.write_text("backup de outra execução em andamento", encoding="utf-8")
    velho = ambiente["backups"] / ".bandejao-20261120T060000Z.tmp"
    velho.write_text("sobra de um backup interrompido", encoding="utf-8")
    os.utime(velho, (time.time() - 2 * DIA,) * 2)
    rodar()
    assert recente.exists()
    assert not velho.exists()


@precisa_de_sh
def test_tempo_limite_do_cliente_encerra_um_docker_travado(rodar, ambiente):
    """Só o `timeout` de dentro do container não basta: se o cliente do docker
    travar, ele segura a trava para sempre."""
    resultado = rodar(SONO_DOCKER="30", BANDEJAO_TEMPO_LIMITE_CLIENTE="1")
    assert resultado.returncode == 1
    assert "tempo esgotado" in resultado.log
    assert copias(ambiente) == []


@precisa_de_sh
def test_tamanho_parecido_com_o_da_copia_anterior_nao_avisa(rodar, ambiente):
    anterior = ambiente["backups"] / "bandejao-20261120T064500Z.sql.gz"
    anterior.write_bytes(gzip.compress(DUMP_COMPLETO.encode()))
    os.utime(anterior, (time.time() - DIA,) * 2)
    resultado = rodar()
    assert not any("menos da metade" in linha for linha in resultado.logger)


@precisa_de_sh
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="precisa de usuário comum no Linux"
)
def test_log_sem_escrita_sai_com_73_antes_de_rodar_o_dump(rodar, ambiente):
    ambiente["logs"].mkdir()
    log = ambiente["logs"] / "backup-banco.log"
    log.write_text("", encoding="utf-8")
    log.chmod(0o400)
    try:
        resultado = rodar()
    finally:
        log.chmod(0o600)
    assert resultado.returncode == 73
    assert "sem permissão de escrita" in resultado.stderr
    assert any("user.err" in linha for linha in resultado.logger)
    assert resultado.docker is None


@precisa_de_sh
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="precisa de usuário comum no Linux"
)
def test_log_do_root_nao_impede_a_rotacao_de_apagar_a_copia_velha(rodar, ambiente):
    """O caso do `sudo`: o log nasceu como root e todo cron sai com 73. As
    cópias com mais de 7 dias têm que sair mesmo assim (RNF07.4), e a pasta
    sem cópia nenhuma tem que avisar com `crit`."""
    ambiente["logs"].mkdir()
    log = ambiente["logs"] / "backup-banco.log"
    log.write_text("", encoding="utf-8")
    log.chmod(0o400)
    velha = criar_copia(ambiente, "bandejao-20261101T064500Z.sql.gz", 8 * DIA)
    try:
        resultado = rodar()
    finally:
        log.chmod(0o600)
    assert resultado.returncode == 73
    assert not velha.exists()
    assert any(
        "user.crit" in linha and "SEM NENHUMA" in linha for linha in resultado.logger
    )


@precisa_de_sh
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="precisa de usuário comum no Linux"
)
def test_saida_73_com_copia_recente_nao_avisa_com_crit(rodar, ambiente):
    ambiente["logs"].mkdir()
    log = ambiente["logs"] / "backup-banco.log"
    log.write_text("", encoding="utf-8")
    log.chmod(0o400)
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 3600)
    try:
        resultado = rodar()
    finally:
        log.chmod(0o600)
    assert resultado.returncode == 73
    assert not any("user.crit" in linha for linha in resultado.logger)


@precisa_de_sh
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="precisa de usuário comum no Linux"
)
def test_trava_de_outro_usuario_sai_com_73_e_avisa(rodar, ambiente):
    trava = ambiente["backups"] / ".trava"
    trava.write_text("", encoding="utf-8")
    trava.chmod(0o400)
    try:
        resultado = rodar()
    finally:
        trava.chmod(0o600)
    assert resultado.returncode == 73
    assert any("user.err" in linha and ".trava" in linha for linha in resultado.logger)


@precisa_de_sh
def test_resumo_e_erros_ficam_no_log_do_proprio_script(rodar, ambiente):
    rodar()
    rodar(falha=1)
    log = (ambiente["logs"] / "backup-banco.log").read_text(encoding="utf-8")
    assert log.count("início do backup") == 2
    assert "ok: bandejao-" in log and "terminou com status 1" in log


@precisa_de_sh
@pytest.mark.skipif(os.name == "nt", reason="precisa de sinais do Linux")
@pytest.mark.parametrize("sinal", [signal.SIGINT, signal.SIGTERM])
def test_interrupcao_apaga_o_dump_sem_compressao(ambiente, sinal):
    """No `sh` (dash), um Ctrl-C ou kill não rodam o trap de EXIT sozinhos:
    sem o `trap 'exit 130' INT TERM`, o dump bruto (dado pessoal sem
    compressão) ficaria na pasta por dias."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BANDEJAO_")}
    env.update(
        PATH=str(ambiente["bin"]) + os.pathsep + os.environ["PATH"],
        SAIDA_DOCKER=ambiente["docker"].as_posix(),
        SAIDA_LOGGER=ambiente["logger"].as_posix(),
        BANDEJAO_BACKUPS=ambiente["backups"].as_posix(),
        BANDEJAO_LOGS=ambiente["logs"].as_posix(),
        DUMP_TEXTO=DUMP_COMPLETO,
        SONO_DOCKER="30",
    )
    processo = subprocess.Popen(
        [SH, BACKUP.as_posix()],
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if list(ambiente["backups"].glob(".bandejao-*.tmp")):
                break
            time.sleep(0.05)
        else:
            pytest.fail("o dump nunca começou")
        os.killpg(processo.pid, sinal)
        assert processo.wait(timeout=20) == 130
    finally:
        if processo.poll() is None:
            os.killpg(processo.pid, signal.SIGKILL)
    assert [p.name for p in ambiente["backups"].glob(".bandejao-*")] == []
    assert copias(ambiente) == []
    # A interrupção deixa rastro no log e no syslog.
    assert "interrompido por sinal" in ler_texto(ambiente["logs"] / "backup-banco.log")
    assert "interrompido por sinal" in ler_texto(ambiente["logger"])


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
@pytest.mark.skipif(shutil.which("flock") is None, reason="sem flock no PATH")
def test_saida_75_com_copia_velha_demais_avisa_com_crit(rodar, ambiente):
    import fcntl

    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 30 * 3600)
    with open(ambiente["backups"] / ".trava", "a") as aberto:
        fcntl.flock(aberto, fcntl.LOCK_EX | fcntl.LOCK_NB)
        resultado = rodar()
    assert resultado.returncode == 75
    assert any("user.crit" in linha for linha in resultado.logger)


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
    run) printf '%s\\n' "${MYSQL_ROOT_PASSWORD:-}" >> "$SAIDA_DOCKER.senha"; exit "${FALHA_RUN:-0}" ;;
    logs)
        if [ -n "${SONO_LOGS:-}" ]; then sleep "$SONO_LOGS"; fi
        echo "MySQL init process done. Ready for start up."; exit 0 ;;
    exec)
        # `exec -i <nome> mysql ...` (restauração): lê o dump da entrada.
        case "$*" in
            *mysqladmin*) exit "${FALHA_PING:-0}" ;;
            *"-i "*) cat > "$SAIDA_DOCKER.dump"; exit "${FALHA_RESTAURAR:-0}" ;;
            *django_migrations*)
                if [ -n "${FALHA_MIGRACOES:-}" ]; then echo "ERROR 1146: Table doesn't exist" >&2; exit 1; fi
                echo "${MIGRACOES:-41}"; exit 0 ;;
            *"FROM cadastro_usuario"*) echo "${USUARIOS_TEMP:-3}"; exit 0 ;;
            *"COUNT(*) FROM information_schema"*) echo "${TABELAS_TEMP:-30}"; exit 0 ;;
            *"SELECT table_name"*)
                if [ -n "${FALHA_LISTA:-}" ]; then echo "ERROR 1045: Access denied" >&2; exit 1; fi
                printf '%s' "${TABELAS_LISTA-cadastro_usuario}"; exit 0 ;;
            *'COUNT(*) FROM `'*) echo "${LINHAS:-3}"; exit 0 ;;
            *) exit 0 ;;
        esac ;;
    compose)
        # A produção também lê a entrada: grava o que chegar nela.
        cat > "$SAIDA_DOCKER.compose_entrada"
        case "$*" in
            *"FROM cadastro_usuario"*) echo "${USUARIOS_PROD:-3}"; exit 0 ;;
            *) echo "${TABELAS_PROD:-30}"; exit 0 ;;
        esac ;;
esac
exit 0
"""


@pytest.fixture
def restaurar(ambiente):
    (ambiente["bin"] / "docker").write_text(
        DOCKER_RESTAURACAO, encoding="utf-8", newline="\n"
    )

    def restaurar(*argumentos, entrada="", **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("BANDEJAO_")}
        env.update(
            PATH=str(ambiente["bin"]) + os.pathsep + os.environ["PATH"],
            SAIDA_DOCKER=ambiente["docker"].as_posix(),
            BANDEJAO_BACKUPS=ambiente["backups"].as_posix(),
            BANDEJAO_ESPERA_TESTE="2",
            BANDEJAO_PAUSA_TESTE="0",
        )
        env.update(extra)
        resultado = subprocess.run(
            [SH, RESTAURACAO.as_posix(), *argumentos],
            check=False,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            input=entrada,
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


@precisa_de_sh
def test_restauracao_sobe_container_sem_rede_e_o_remove(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar()
    chamadas = resultado.docker
    run = next(c for c in chamadas if c.startswith("run "))
    assert "--network none" in run and "--rm" in run and "mysql:8.4" in run
    # A senha vai pelo ambiente (`-e NOME`, sem valor), nunca como argumento.
    assert "-e MYSQL_ROOT_PASSWORD " in run and "MYSQL_ROOT_PASSWORD=" not in run
    assert chamadas[-1].startswith("rm -f -v bandejao-teste-restauracao")
    # Nenhum comando do docker leva a senha na linha de comando.
    senha = ler_texto(Path(str(ambiente["docker"]) + ".senha")).strip()
    assert senha and not any(senha in c for c in chamadas)


@precisa_de_sh
def test_restauracao_usa_senha_aleatoria_diferente_a_cada_vez(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    restaurar()
    restaurar()
    senhas = ler_texto(Path(str(ambiente["docker"]) + ".senha")).split()
    assert len(senhas) == 2 and senhas[0] != senhas[1]
    assert all(re.fullmatch(r"[0-9a-f]{48}", s) for s in senhas)


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
    assert resultado.docker[-1].startswith("rm -f -v")


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


@precisa_de_sh
def test_restauracao_sem_contas_falha_mesmo_com_outras_tabelas_povoadas(
    restaurar, ambiente
):
    """Um `down -v` seguido de `migrate` gera um dump completo e sem contas, e
    a tabela de cache do limite de taxa enche com uma tentativa de login:
    `LINHAS` (as outras tabelas) não pode esconder o `cadastro_usuario` vazio."""
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(LINHAS="50", USUARIOS_TEMP="0", USUARIOS_PROD="3")
    assert resultado.returncode == 1
    assert "cadastro_usuario restaurado está vazio" in resultado.stderr
    assert "OK:" not in resultado.stdout


@precisa_de_sh
@pytest.mark.parametrize(
    ("temp", "prod", "passa"),
    [(1, 3, False), (2, 3, True), (3, 3, True), (0, 0, True), (5, 3, True)],
)
def test_restauracao_compara_as_contas_com_a_producao(
    restaurar, ambiente, temp, prod, passa
):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(USUARIOS_TEMP=str(temp), USUARIOS_PROD=str(prod))
    assert (resultado.returncode == 0) is passa
    if not passa:
        assert "menos da metade" in resultado.stderr


@precisa_de_sh
def test_restauracao_com_lista_de_tabelas_vazia_falha(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(TABELAS_LISTA="")
    assert resultado.returncode == 1
    assert "lista de tabelas" in resultado.stderr
    assert "OK:" not in resultado.stdout


@precisa_de_sh
def test_restauracao_mostra_o_erro_do_mysql_na_falha_da_listagem(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(FALHA_LISTA="1")
    assert resultado.returncode == 1
    assert "não consegui listar" in resultado.stderr
    assert "Access denied" in resultado.stderr


@precisa_de_sh
def test_restauracao_distingue_erro_de_sql_de_tabela_ausente(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(FALHA_MIGRACOES="1")
    assert resultado.returncode == 1
    assert "não consegui contar django_migrations" in resultado.stderr
    assert "Table doesn't exist" in resultado.stderr


@precisa_de_sh
def test_restauracao_nao_deixa_o_arquivo_de_erros(restaurar, ambiente, tmp_path):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    pasta_tmp = tmp_path / "tmp"
    pasta_tmp.mkdir()
    restaurar(TMPDIR=pasta_tmp.as_posix())
    restaurar(TMPDIR=pasta_tmp.as_posix(), FALHA_LISTA="1")
    assert list(pasta_tmp.iterdir()) == []


@precisa_de_sh
def test_consulta_de_producao_nao_le_o_teclado_nem_leva_senha(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(entrada="digitado no terminal")
    assert resultado.returncode == 0, resultado.stderr
    entrada = Path(str(ambiente["docker"]) + ".compose_entrada")
    assert entrada.read_text(encoding="utf-8") == ""
    # Toda chamada que roda o `mysql` passa a senha por MYSQL_PWD, e nenhuma
    # leva `-p` ou `--password` na linha de comando.
    chamadas_mysql = [c for c in resultado.docker if "mysql" in c and "run" != c[:3]]
    assert chamadas_mysql
    for chamada in chamadas_mysql:
        assert "MYSQL_PWD=" in chamada, chamada
        assert not SENHA_NA_LINHA.search(chamada), chamada


@precisa_de_sh
@pytest.mark.parametrize("banco", ["a b", "x;y", "x'y"])
def test_restauracao_com_nome_de_banco_invalido_sai_com_2_sem_docker(
    restaurar, ambiente, banco
):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(BANDEJAO_BANCO=banco)
    assert resultado.returncode == 2
    assert resultado.docker == []


@precisa_de_sh
@pytest.mark.parametrize("variavel", ["BANDEJAO_ESPERA_TESTE", "BANDEJAO_PAUSA_TESTE"])
def test_restauracao_com_espera_nao_numerica_sai_com_2(restaurar, ambiente, variavel):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(**{variavel: "dois"})
    assert resultado.returncode == 2
    assert resultado.docker == []


@precisa_de_sh
def test_restauracao_so_vale_com_o_mysqladmin_ping_respondendo(restaurar, ambiente):
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    resultado = restaurar(FALHA_PING="1", BANDEJAO_ESPERA_TESTE="1")
    assert resultado.returncode == 1
    assert "não ficou pronto a tempo" in resultado.stderr
    assert any("mysqladmin" in c for c in resultado.docker)


@precisa_de_sh
def test_restauracao_espera_o_fim_do_init_do_mysql(restaurar, ambiente):
    """Só vale depois de 'MySQL init process done': um `grep -q .` aceitaria
    qualquer linha de log do servidor provisório."""
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    docker = ambiente["bin"] / "docker"
    sem_o_fim_do_init = DOCKER_RESTAURACAO.replace(
        'echo "MySQL init process done. Ready for start up."',
        'echo "Temporary server started."',
    )
    assert sem_o_fim_do_init != DOCKER_RESTAURACAO  # a troca aconteceu
    docker.write_text(sem_o_fim_do_init, encoding="utf-8", newline="\n")
    resultado = restaurar(BANDEJAO_ESPERA_TESTE="1")
    assert resultado.returncode == 1
    assert "não ficou pronto a tempo" in resultado.stderr
    assert resultado.docker[-1].startswith("rm -f -v")


@precisa_de_sh
@pytest.mark.skipif(os.name == "nt", reason="precisa de sinais do Linux")
@pytest.mark.parametrize("sinal", [signal.SIGINT, signal.SIGTERM])
def test_interrupcao_remove_o_container_temporario(restaurar, ambiente, sinal):
    """O container tem uma cópia inteira da produção e o `--rm` só age quando
    ele para: um Ctrl-C ou kill têm que acionar o `docker rm -f -v`."""
    criar_copia(ambiente, "bandejao-20261120T064500Z.sql.gz", 1 * DIA)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BANDEJAO_")}
    env.update(
        PATH=str(ambiente["bin"]) + os.pathsep + os.environ["PATH"],
        SAIDA_DOCKER=ambiente["docker"].as_posix(),
        BANDEJAO_BACKUPS=ambiente["backups"].as_posix(),
        SONO_LOGS="30",
    )
    processo = subprocess.Popen(
        [SH, RESTAURACAO.as_posix()],
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if any(c.startswith("logs ") for c in ler_linhas(ambiente["docker"]) or []):
                break
            time.sleep(0.05)
        else:
            pytest.fail("a restauração nunca começou a esperar o MySQL")
        os.killpg(processo.pid, sinal)
        assert processo.wait(timeout=20) == 130
    finally:
        if processo.poll() is None:
            os.killpg(processo.pid, signal.SIGKILL)
    assert ler_linhas(ambiente["docker"])[-1].startswith("rm -f -v")
