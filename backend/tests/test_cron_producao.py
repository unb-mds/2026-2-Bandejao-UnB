"""Cron do sistema operacional da VM de produção (BD-07, #147).

ADRs 0003, 0007, 0012 e 0014: as tarefas periódicas são comandos do Django
chamados pelo cron da VM, e não um componente da aplicação. Ficam em
`deploy/cron/`:

- `bandejao`: o arquivo do `/etc/cron.d/` (com o campo de usuário);
- `rodar-comando.sh`: roda um comando no container do backend, com log,
  tempo limite, aviso no syslog em caso de falha e trava contra duas
  execuções ao mesmo tempo;
- `logrotate`: a rotação dos logs, para não encher o disco da VM.

O cron de verdade só existe na VM; aqui o arquivo é lido como texto, e o
script roda com um `docker` e um `logger` falsos no PATH, que só gravam o que
receberam.
"""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from django.core.management import get_commands

RAIZ = Path(__file__).resolve().parents[2]
CRON = RAIZ / "deploy" / "cron"
CRONTAB = CRON / "bandejao"
SCRIPT = CRON / "rodar-comando.sh"
LOGROTATE = CRON / "logrotate"
PASTA_NA_VM = "/home/azureuser/2026-2-Bandejao-UnB"

# Comando -> agenda (campos de minuto a dia da semana, em UTC, o fuso da VM).
AGENDA_ESPERADA = {
    # RF02.3: o pendente sai logo depois das 24 h, e a matrícula fica livre.
    "excluir_cadastros_pendentes": "0 * * * *",
    # ADR 0014: de 3 em 3 horas, todos os dias.
    "ler_cardapio": "0 */3 * * *",
}
DIARIOS = {"clearsessions", "desvincular_registros_fila"}
TODOS = set(AGENDA_ESPERADA) | DIARIOS

# Comandos que ainda vão entrar na `develop` por outro PR ({nome: "PR"}). Até
# lá, a linha deles fica comentada no `bandejao`, para o cron não chamar um
# comando que não existe; quando o comando existir,
# `test_tarefa_ativa_se_e_so_se_o_comando_existe` falha até a linha ser
# descomentada. Foi assim com o `ler_cardapio`, até o #218.
PENDENTES: dict[str, str] = {}

LINHA_DE_TAREFA = re.compile(
    rf"^(?P<agenda>(?:\S+\s+){{5}})(?P<usuario>\S+)\s+"
    rf"sh {re.escape(PASTA_NA_VM)}/deploy/cron/rodar-comando\.sh (?P<resto>.+)$"
)


def tarefas_do_crontab():
    """{comando: (agenda, usuário, argumentos, ativa)}. Uma linha de tarefa
    comentada com "# " conta como desativada."""
    resultado = {}
    for linha in CRONTAB.read_text(encoding="utf-8").splitlines():
        texto = linha.strip()
        ativa = not texto.startswith("#")
        if not ativa:
            texto = texto.lstrip("#").strip()
        encontrada = LINHA_DE_TAREFA.match(texto)
        if not encontrada:
            # Linha ativa que não é variável nem vazia tem que ser tarefa.
            assert not ativa or not texto or re.match(r"^[A-Z_]+=", texto), (
                f"linha fora do formato do cron.d: {linha}"
            )
            continue
        partes = encontrada["resto"].split()
        nome = partes[0]
        assert nome not in resultado, f"{nome} aparece duas vezes"
        resultado[nome] = (
            " ".join(encontrada["agenda"].split()),
            encontrada["usuario"],
            partes,
            ativa,
        )
    return resultado


def ativas():
    return {nome: t for nome, t in tarefas_do_crontab().items() if t[3]}


# --- deploy/cron/bandejao ---------------------------------------------------


def test_cron_tem_os_quatro_comandos_da_bd07():
    assert set(tarefas_do_crontab()) == TODOS


@pytest.mark.parametrize("comando", sorted(TODOS))
def test_tarefa_ativa_se_e_so_se_o_comando_existe(comando):
    """Um comando que ainda não existe fica comentado; quando ele existir,
    a linha tem que ser descomentada."""
    existe = comando in get_commands()
    ativa = tarefas_do_crontab()[comando][3]
    if existe:
        assert ativa, f"{comando} já existe: descomente a linha no bandejao"
    else:
        assert comando in PENDENTES, f"{comando} não é um comando do Django"
        assert not ativa, f"{comando} ainda não existe: comente a linha"


@pytest.mark.parametrize(("comando", "agenda"), AGENDA_ESPERADA.items())
def test_agenda_dos_comandos_frequentes(comando, agenda):
    assert tarefas_do_crontab()[comando][0] == agenda


@pytest.mark.parametrize("comando", sorted(DIARIOS))
def test_diarios_rodam_uma_vez_de_madrugada_em_brasilia(comando):
    """Uma vez por dia, antes das 6h de Brasília (UTC-3), longe das
    refeições, e fora do minuto 0, quando rodam o cardápio e a exclusão de
    pendentes."""
    minuto, hora, dia, mes, semana = tarefas_do_crontab()[comando][0].split()
    assert (dia, mes, semana) == ("*", "*", "*")
    assert minuto.isdigit() and hora.isdigit()
    assert 3 <= int(hora) <= 8
    assert int(minuto) != 0


def test_diarios_nao_rodam_no_mesmo_minuto():
    horarios = [tarefas_do_crontab()[comando][0] for comando in DIARIOS]
    assert len(set(horarios)) == len(horarios)


def test_tarefas_rodam_como_o_usuario_do_deploy():
    """O `azureuser`, que está no grupo docker na VM (conferência no guia);
    o root não é preciso."""
    usuarios = {t[1] for t in tarefas_do_crontab().values()}
    assert usuarios == {"azureuser"}


def test_comandos_so_com_o_nome_sem_argumentos():
    for nome, (_, _, partes, _) in tarefas_do_crontab().items():
        assert partes == [nome], f"{nome}: argumento inesperado"


def test_crontab_define_shell_e_path():
    """O cron roda com um PATH mínimo; sem o `/usr/bin`, o `docker` não acha."""
    texto = CRONTAB.read_text(encoding="utf-8")
    assert re.search(r"^SHELL=/bin/sh$", texto, re.MULTILINE)
    caminho = re.search(r"^PATH=(.+)$", texto, re.MULTILINE)
    assert caminho
    assert "/usr/bin" in caminho.group(1).split(":")


# Todos os arquivos de deploy/, para um arquivo novo entrar sozinho.
ARQUIVOS_DE_DEPLOY = sorted(p for p in (RAIZ / "deploy").rglob("*") if p.is_file())


def test_arquivos_de_deploy_encontrados():
    assert {CRONTAB, SCRIPT, LOGROTATE} <= set(ARQUIVOS_DE_DEPLOY)


@pytest.mark.parametrize("arquivo", ARQUIVOS_DE_DEPLOY, ids=lambda p: p.name)
def test_arquivos_terminam_com_quebra_de_linha_e_sem_crlf(arquivo):
    """O cron ignora a última linha sem `\\n`; um `\\r` entra no comando e a
    tarefa falha."""
    conteudo = arquivo.read_bytes()
    assert conteudo.endswith(b"\n")
    assert b"\r" not in conteudo


def test_nome_do_arquivo_vale_no_cron_d():
    """O cron ignora arquivos do `/etc/cron.d/` com ponto no nome."""
    assert re.fullmatch(r"[A-Za-z0-9_-]+", CRONTAB.name)


# --- deploy/cron/logrotate e .gitattributes ---------------------------------


def test_logrotate_cobre_os_logs_do_cron():
    texto = LOGROTATE.read_text(encoding="utf-8")
    assert "/var/log/bandejao/*.log" in texto
    rotacao = re.search(r"^\s*rotate\s+(\d+)\s*$", texto, re.MULTILINE)
    assert rotacao and int(rotacao.group(1)) >= 1
    for opcao in ("missingok", "compress"):
        assert re.search(rf"^\s*{opcao}\s*$", texto, re.MULTILINE), opcao


GIT = shutil.which("git")


@pytest.mark.skipif(GIT is None, reason="sem git no PATH")
@pytest.mark.parametrize("arquivo", ARQUIVOS_DE_DEPLOY, ids=lambda p: p.name)
def test_git_grava_os_arquivos_do_cron_com_lf(arquivo):
    """Num clone no Windows, o Git troca o LF por CRLF sem a regra."""
    resultado = subprocess.run(
        [GIT, "check-attr", "eol", "--", arquivo.relative_to(RAIZ).as_posix()],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        text=True,
    )
    assert resultado.stdout.strip().endswith("eol: lf")


# --- deploy/cron/rodar-comando.sh com docker e logger falsos ---------------

SH = shutil.which("sh")
TEM_FLOCK = shutil.which("flock") is not None
precisa_de_sh = pytest.mark.skipif(SH is None, reason="sem sh no PATH")
precisa_de_flock = pytest.mark.skipif(
    SH is None or not TEM_FLOCK, reason="sem sh ou flock no PATH"
)

DOCKER_FALSO = """#!/bin/sh
# `pwd -W` dá o caminho do Windows no sh do Git; no Linux, vale o `pwd`.
{ pwd -W 2>/dev/null || pwd; } > "$SAIDA_DOCKER"
for arg in "$@"; do printf '%s\\n' "$arg" >> "$SAIDA_DOCKER"; done
# Com LER_STDIN, lê a entrada como o `docker compose exec -T` num terminal:
# se ela estiver aberta, espera para sempre.
if [ -n "${LER_STDIN:-}" ]; then cat > "$SAIDA_DOCKER.stdin"; fi
echo "saida-do-comando"
if [ -n "${ESPERA_DOCKER:-}" ]; then sleep "$ESPERA_DOCKER"; fi
echo x >> "$SAIDA_DOCKER.vezes"
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
    return {
        "bin": bin_falso,
        "logs": tmp_path / "logs",
        "docker": tmp_path / "docker.txt",
        "logger": tmp_path / "logger.txt",
    }


@pytest.fixture
def rodar(ambiente):
    def rodar(
        *argumentos,
        falha=None,
        espera=None,
        fundo=False,
        caminho=None,
        stdin=None,
        **extra,
    ):
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "FALHA_DOCKER",
                "ESPERA_DOCKER",
                "LER_STDIN",
                "BANDEJAO_TEMPO_LIMITE",
                "BANDEJAO_TEMPO_LIMITE_CLIENTE",
            )
        }
        env.update(
            PATH=str(ambiente["bin"]) + os.pathsep + (caminho or os.environ["PATH"]),
            SAIDA_DOCKER=ambiente["docker"].as_posix(),
            SAIDA_LOGGER=ambiente["logger"].as_posix(),
            BANDEJAO_LOGS=ambiente["logs"].as_posix(),
        )
        env.update(extra)
        if falha is not None:
            env["FALHA_DOCKER"] = str(falha)
        if espera is not None:
            env["ESPERA_DOCKER"] = str(espera)
        comando = [SH, SCRIPT.as_posix(), *argumentos]
        if fundo:
            return subprocess.Popen(comando, env=env, stdin=stdin)
        resultado = subprocess.run(
            comando,
            check=False,  # o status de saída é conferido pelos testes
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        resultado.docker = ler_linhas(ambiente["docker"])
        resultado.logger = ler_linhas(ambiente["logger"]) or []
        resultado.logs = ambiente["logs"]
        return resultado

    return rodar


def ler_linhas(arquivo):
    return (
        arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else None
    )


def log_de(resultado, comando):
    return (resultado.logs / f"{comando}.log").read_text(encoding="utf-8")


def chamadas_do_docker_terminadas(resultado):
    """Quantas vezes o docker falso chegou ao fim (o `.vezes` é gravado no
    final dele)."""
    vezes = resultado.logs.parent / "docker.txt.vezes"
    return len(ler_linhas(vezes) or [])


def chamadas_do_docker(ambiente):
    vezes = ambiente["docker"].with_name("docker.txt.vezes")
    return len(ler_linhas(vezes) or [])


@precisa_de_sh
def test_roda_o_comando_no_container_com_tempo_limite(rodar):
    resultado = rodar("clearsessions")

    assert resultado.returncode == 0
    pasta, *argumentos = resultado.docker
    assert argumentos == [
        "compose",
        "exec",
        "-T",
        "backend",
        # O `timeout` roda dentro do container: quando o tempo acaba, quem
        # morre é o processo do Django, e não só o cliente do docker.
        "timeout",
        "--kill-after=60",
        "2h",
        "python",
        "manage.py",
        "clearsessions",
    ]
    # Da pasta do repositório, onde estão o docker-compose.yml e o .env.
    assert Path(pasta).resolve() == RAIZ.resolve()


@precisa_de_sh
def test_nao_le_o_terminal_ao_rodar_a_mao(rodar, ambiente):
    """Rodando à mão por SSH, a entrada é o terminal, aberta e sem dados. O
    `docker compose exec -T` ficava lendo dela e o script travava em silêncio.
    Aqui a entrada é um pipe que ninguém fecha: se o script a repassar ao
    docker, o `cat` do docker falso espera e o teste estoura o tempo."""
    processo = rodar("clearsessions", fundo=True, LER_STDIN="1", stdin=subprocess.PIPE)
    try:
        status = processo.wait(timeout=20)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait()
        pytest.fail("o script ficou esperando a entrada: o docker leu o terminal")
    finally:
        processo.stdin.close()

    assert status == 0
    stdin_do_docker = ambiente["docker"].with_name("docker.txt.stdin")
    assert stdin_do_docker.read_text(encoding="utf-8") == ""


@precisa_de_sh
def test_tempo_limite_pode_ser_trocado(rodar):
    resultado = rodar("clearsessions", BANDEJAO_TEMPO_LIMITE="30m")

    assert resultado.docker[5:8] == ["timeout", "--kill-after=60", "30m"]


@precisa_de_sh
def test_tempo_esgotado_vai_para_o_log_e_para_o_syslog(rodar):
    resultado = rodar("ler_cardapio", falha=124)

    assert resultado.returncode == 124
    log = log_de(resultado, "ler_cardapio")
    assert "tempo esgotado" in log
    assert log.splitlines()[-1].endswith("fim: status 124")
    assert any(
        "-p user.err" in chamada and "ler_cardapio" in chamada
        for chamada in resultado.logger
    )


@precisa_de_sh
def test_encerrado_com_kill_vai_para_o_log(rodar):
    """Se o processo ignora o TERM, o `--kill-after` mata com KILL e o
    `timeout` sai com 137 (128 + 9), e não com 124."""
    resultado = rodar("ler_cardapio", falha=137)

    assert resultado.returncode == 137
    assert "encerrado à força" in log_de(resultado, "ler_cardapio")


@precisa_de_sh
def test_cliente_do_docker_travado_tambem_tem_tempo_limite(rodar):
    """Um `timeout` no host, um pouco maior que o do container, cobre o
    `docker compose exec` travado (daemon sem resposta), que seguraria a
    trava para sempre."""
    resultado = rodar("ler_cardapio", espera=10, BANDEJAO_TEMPO_LIMITE_CLIENTE="1s")

    assert resultado.returncode == 124
    assert "tempo esgotado" in log_de(resultado, "ler_cardapio")
    assert chamadas_do_docker_terminadas(resultado) == 0


@precisa_de_sh
def test_grava_inicio_saida_e_fim_no_log_do_comando(rodar):
    resultado = rodar("clearsessions")

    linhas = log_de(resultado, "clearsessions").splitlines()
    assert re.fullmatch(
        r"\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\] início: clearsessions", linhas[0]
    )
    assert "saida-do-comando" in linhas
    assert re.fullmatch(r"\[.+Z\] fim: status 0", linhas[-1])


@precisa_de_sh
def test_sucesso_nao_vai_para_o_syslog(rodar):
    resultado = rodar("clearsessions")

    assert not any("user.err" in chamada for chamada in resultado.logger)


@precisa_de_sh
def test_log_acumula_as_execucoes(rodar):
    rodar("clearsessions")
    resultado = rodar("clearsessions")

    assert log_de(resultado, "clearsessions").count("início: clearsessions") == 2


@precisa_de_sh
def test_falha_do_comando_vai_para_o_log_o_status_e_o_syslog(rodar):
    resultado = rodar("excluir_cadastros_pendentes", falha=3)

    assert resultado.returncode == 3
    log = log_de(resultado, "excluir_cadastros_pendentes")
    assert log.splitlines()[-1].endswith("fim: status 3")
    assert any(
        "-p user.err" in chamada
        and "-t bandejao-cron" in chamada
        and "excluir_cadastros_pendentes" in chamada
        and "status 3" in chamada
        for chamada in resultado.logger
    )


@precisa_de_sh
def test_status_75_do_comando_nao_vira_pulado(rodar):
    """O 75 é do comando, e não da trava: a execução não foi pulada."""
    resultado = rodar("clearsessions", falha=75)

    assert resultado.returncode == 75
    assert "pulado" not in log_de(resultado, "clearsessions")
    # No syslog também: é erro do comando, e não um pulo normal.
    assert any(
        "-p user.err" in chamada and "status 75" in chamada
        for chamada in resultado.logger
    )
    assert not any("pulado" in chamada for chamada in resultado.logger)


@precisa_de_sh
@pytest.mark.parametrize(
    "nome", ["", "Clear", "clear sessions", "../x", "x;id", "-h", "x$(id)"]
)
def test_nome_de_comando_invalido_nao_chega_ao_docker(rodar, nome):
    resultado = rodar(nome)

    assert resultado.returncode == 2
    assert resultado.docker is None
    assert "comando inválido" in resultado.stderr
    # Sem MTA na VM, o stderr do cron se perde: o erro vai para o syslog.
    assert any("comando inválido" in chamada for chamada in resultado.logger)


@precisa_de_sh
def test_sem_comando_mostra_o_uso_e_avisa_o_syslog(rodar):
    resultado = rodar()

    assert resultado.returncode == 2
    assert resultado.docker is None
    assert "uso:" in resultado.stderr
    assert any("uso:" in chamada for chamada in resultado.logger)


@precisa_de_sh
def test_argumentos_extras_sao_repassados(rodar):
    """Para rodar à mão com uma opção do comando; o cron não passa
    argumentos. Um argumento com espaço chega inteiro."""
    resultado = rodar("clearsessions", "--verbosity", "2", "a b")

    assert resultado.docker[-4:] == ["clearsessions", "--verbosity", "2", "a b"]


@precisa_de_sh
def test_pasta_de_logs_que_nao_pode_ser_criada(rodar, ambiente, tmp_path):
    """`mkdir` falha (aqui, porque o caminho é um arquivo): sai com erro, não
    chama o docker e avisa o syslog."""
    arquivo = tmp_path / "nao-e-pasta"
    arquivo.write_text("x", encoding="utf-8")

    resultado = rodar("clearsessions", BANDEJAO_LOGS=(arquivo / "logs").as_posix())

    assert resultado.returncode == 1
    assert resultado.docker is None
    assert "não foi possível criar" in resultado.stderr
    assert any(
        "-p user.err" in chamada and "não foi possível criar" in chamada
        for chamada in resultado.logger
    )


@precisa_de_sh
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="o root grava mesmo em arquivo sem permissão",
)
@pytest.mark.parametrize("arquivo", ["clearsessions.log", "clearsessions.lock"])
def test_log_sem_permissao_de_escrita_nao_para_em_silencio(rodar, ambiente, arquivo):
    """O caso de quem rodou o script com sudo uma vez: o log fica do root e o
    `azureuser` não grava mais. A tarefa avisa o syslog e sai com 73, sem
    chamar o docker (e sem o `status: parameter not set` do `set -u`)."""
    ambiente["logs"].mkdir()
    sem_escrita = ambiente["logs"] / arquivo
    sem_escrita.write_text("", encoding="utf-8")
    sem_escrita.chmod(stat.S_IREAD)
    try:
        resultado = rodar("clearsessions")
    finally:
        sem_escrita.chmod(stat.S_IREAD | stat.S_IWRITE)

    assert resultado.returncode == 73
    assert resultado.docker is None
    assert "parameter not set" not in resultado.stderr
    assert any(
        "-p user.err" in chamada and arquivo in chamada for chamada in resultado.logger
    )


@precisa_de_sh
def test_sem_flock_avisa_no_log_que_rodou_sem_trava(rodar, tmp_path):
    """Onde há `flock` (o CI), o PATH fica só com o que o script usa, sem
    ele; no sh do Git, que não tem `flock`, vale o PATH normal."""
    caminho = None
    if TEM_FLOCK:
        minimo = tmp_path / "bin-minimo"
        minimo.mkdir()
        for nome in ("dirname", "mkdir", "date", "timeout", "sleep"):
            (minimo / nome).symlink_to(shutil.which(nome))
        caminho = str(minimo)
        assert shutil.which("flock", path=caminho) is None

    resultado = rodar("clearsessions", caminho=caminho)

    assert resultado.returncode == 0
    assert "sem flock" in log_de(resultado, "clearsessions")


def esperar_o_docker(ambiente, popen):
    for _ in range(100):
        if ambiente["docker"].exists():
            return
        try:
            popen.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            continue
    pytest.fail("a primeira execução não chegou ao docker")


@precisa_de_flock
def test_segunda_execucao_simultanea_e_pulada(rodar, ambiente):
    """O `ler_cardapio` pode demorar mais que o intervalo do cron; a segunda
    execução não roda por cima da primeira."""
    primeira = rodar("ler_cardapio", espera=3, fundo=True)
    try:
        esperar_o_docker(ambiente, primeira)
        resultado = rodar("ler_cardapio")
        primeira.wait(timeout=10)
    finally:
        if primeira.poll() is None:
            primeira.kill()

    assert primeira.returncode == 0
    assert resultado.returncode == 75
    assert chamadas_do_docker(ambiente) == 1
    log = log_de(resultado, "ler_cardapio")
    assert "pulado: a execução anterior ainda está rodando" in log
    assert any("user.warning" in chamada for chamada in resultado.logger)


@precisa_de_flock
def test_trava_e_liberada_depois_da_execucao(rodar, ambiente):
    rodar("ler_cardapio")
    resultado = rodar("ler_cardapio")

    assert resultado.returncode == 0
    assert chamadas_do_docker(ambiente) == 2
