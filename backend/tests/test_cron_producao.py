"""Cron do sistema operacional da VM de produção (BD-07, #147).

ADRs 0003, 0007, 0012 e 0014: as tarefas periódicas são comandos do Django
chamados pelo cron da VM, e não um componente da aplicação. Ficam em
`deploy/cron/`:

- `bandejao`: o arquivo do `/etc/cron.d/` (com o campo de usuário);
- `rodar-comando.sh`: roda um comando no container do backend, com log e
  trava contra duas execuções ao mesmo tempo;
- `logrotate`: a rotação dos logs, para não encher o disco da VM.

O cron de verdade só existe na VM; aqui o arquivo é lido como texto, e o
script roda com um `docker` falso no PATH, que só grava o que recebeu.
"""

import os
import re
import shutil
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

# Comandos que entram na `develop` por outro PR. Enquanto não existem, o teste
# de existência é pulado com o motivo; depois do merge, ele passa a conferir
# de verdade, sem precisar mexer aqui. Um nome errado no cron continua
# falhando, porque só estes dois podem ser pulados.
PENDENTES = {
    "ler_cardapio": "BE-12, #218",
    "desvincular_registros_fila": "BD-11, #220",
}


def linhas_do_crontab():
    linhas = []
    for linha in CRONTAB.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or re.match(r"^[A-Z_]+=", linha):
            continue
        campos = linha.split(None, 6)
        assert len(campos) == 7, f"linha fora do formato do cron.d: {linha}"
        linhas.append(campos)
    return linhas


def tarefas():
    """{comando: (agenda, usuário, linha de comando)}"""
    resultado = {}
    for campos in linhas_do_crontab():
        agenda, usuario, comando = " ".join(campos[:5]), campos[5], campos[6]
        partes = comando.split()
        assert partes[:2] == ["sh", f"{PASTA_NA_VM}/deploy/cron/rodar-comando.sh"], (
            f"a tarefa precisa passar pelo rodar-comando.sh: {comando}"
        )
        nome = partes[2]
        assert nome not in resultado, f"{nome} aparece duas vezes"
        resultado[nome] = (agenda, usuario, partes)
    return resultado


# --- deploy/cron/bandejao ---------------------------------------------------


def test_cron_roda_os_quatro_comandos_da_bd07():
    assert set(tarefas()) == set(AGENDA_ESPERADA) | DIARIOS


@pytest.mark.parametrize(("comando", "agenda"), AGENDA_ESPERADA.items())
def test_agenda_dos_comandos_frequentes(comando, agenda):
    assert tarefas()[comando][0] == agenda


@pytest.mark.parametrize("comando", sorted(DIARIOS))
def test_diarios_rodam_uma_vez_de_madrugada_em_brasilia(comando):
    """Uma vez por dia, entre 0h e 6h de Brasília (UTC-3): longe das
    refeições e fora dos minutos cheios, quando roda o cardápio."""
    minuto, hora, dia, mes, semana = tarefas()[comando][0].split()
    assert (dia, mes, semana) == ("*", "*", "*")
    assert minuto.isdigit() and hora.isdigit()
    assert 3 <= int(hora) <= 8
    assert int(minuto) != 0


def test_diarios_nao_rodam_no_mesmo_minuto():
    horarios = [tarefas()[comando][0] for comando in DIARIOS]
    assert len(set(horarios)) == len(horarios)


def test_tarefas_rodam_como_o_usuario_do_deploy():
    """O `azureuser` está no grupo docker (ADR 0012); o root não é preciso."""
    assert {usuario for _, usuario, _ in tarefas().values()} == {"azureuser"}


def test_comandos_so_com_o_nome_sem_argumentos():
    for nome, (_, _, partes) in tarefas().items():
        assert partes[2:] == [nome], f"{nome}: argumento inesperado"


def test_crontab_define_shell_e_path():
    """O cron roda com um PATH mínimo; sem o `/usr/bin`, o `docker` não acha."""
    texto = CRONTAB.read_text(encoding="utf-8")
    assert re.search(r"^SHELL=/bin/sh$", texto, re.MULTILINE)
    caminho = re.search(r"^PATH=(.+)$", texto, re.MULTILINE)
    assert caminho
    assert "/usr/bin" in caminho.group(1).split(":")


def test_crontab_termina_com_quebra_de_linha_e_sem_crlf():
    """O cron ignora a última linha sem `\\n`, e um `\\r` vira parte do comando."""
    conteudo = CRONTAB.read_bytes()
    assert conteudo.endswith(b"\n")
    assert b"\r" not in conteudo


def test_nome_do_arquivo_vale_no_cron_d():
    """O cron ignora arquivos do `/etc/cron.d/` com ponto no nome."""
    assert re.fullmatch(r"[A-Za-z0-9_-]+", CRONTAB.name)


# --- os comandos existem no Django -----------------------------------------


@pytest.mark.parametrize("comando", sorted(set(AGENDA_ESPERADA) | DIARIOS))
def test_comando_existe_no_django(comando):
    if comando in PENDENTES and comando not in get_commands():
        pytest.skip(f"{comando} entra com o {PENDENTES[comando]}")
    assert comando in get_commands()


# --- deploy/cron/logrotate -------------------------------------------------


def test_logrotate_cobre_os_logs_do_cron():
    texto = LOGROTATE.read_text(encoding="utf-8")
    assert "/var/log/bandejao/*.log" in texto
    rotacao = re.search(r"^\s*rotate\s+(\d+)\s*$", texto, re.MULTILINE)
    assert rotacao and int(rotacao.group(1)) >= 1
    for opcao in ("missingok", "compress"):
        assert re.search(rf"^\s*{opcao}\s*$", texto, re.MULTILINE), opcao


def test_arquivos_do_cron_ficam_com_lf_no_git():
    """Num clone no Windows, o Git troca o LF por CRLF sem a regra."""
    texto = (RAIZ / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(r"^deploy/\*\* text eol=lf$", texto, re.MULTILINE)


# --- deploy/cron/rodar-comando.sh com um docker falso ----------------------

SH = shutil.which("sh")
precisa_de_sh = pytest.mark.skipif(SH is None, reason="sem sh no PATH")

DOCKER_FALSO = """#!/bin/sh
# `pwd -W` dá o caminho do Windows no sh do Git; no Linux, vale o `pwd`.
{ pwd -W 2>/dev/null || pwd; } > "$SAIDA_DOCKER"
for arg in "$@"; do printf '%s\\n' "$arg" >> "$SAIDA_DOCKER"; done
echo "saida-do-comando"
if [ -n "${ESPERA_DOCKER:-}" ]; then sleep "$ESPERA_DOCKER"; fi
exit "${FALHA_DOCKER:-0}"
"""


@pytest.fixture
def rodar(tmp_path):
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    docker = bin_falso / "docker"
    docker.write_text(DOCKER_FALSO, encoding="utf-8", newline="\n")
    docker.chmod(0o755)
    logs = tmp_path / "logs"
    saida = tmp_path / "docker.txt"

    def rodar(*argumentos, falha=None, espera=None, fundo=False):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FALHA_DOCKER", "ESPERA_DOCKER")
        }
        env.update(
            PATH=str(bin_falso) + os.pathsep + os.environ["PATH"],
            SAIDA_DOCKER=saida.as_posix(),
            BANDEJAO_LOGS=logs.as_posix(),
        )
        if falha is not None:
            env["FALHA_DOCKER"] = str(falha)
        if espera is not None:
            env["ESPERA_DOCKER"] = str(espera)
        comando = [SH, SCRIPT.as_posix(), *argumentos]
        if fundo:
            return subprocess.Popen(comando, env=env)
        resultado = subprocess.run(
            comando,
            check=False,  # o status de saída é conferido pelos testes
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        resultado.docker = (
            saida.read_text(encoding="utf-8").splitlines() if saida.exists() else None
        )
        resultado.logs = logs
        return resultado

    return rodar


def log_de(resultado, comando):
    return (resultado.logs / f"{comando}.log").read_text(encoding="utf-8")


@precisa_de_sh
def test_roda_o_comando_no_container_do_backend(rodar):
    resultado = rodar("clearsessions")

    assert resultado.returncode == 0
    pasta, *argumentos = resultado.docker
    assert argumentos == [
        "compose",
        "exec",
        "-T",
        "backend",
        "python",
        "manage.py",
        "clearsessions",
    ]
    # Da pasta do repositório, onde estão o docker-compose.yml e o .env.
    assert Path(pasta).resolve() == RAIZ.resolve()


@precisa_de_sh
def test_grava_inicio_saida_e_fim_no_log_do_comando(rodar):
    resultado = rodar("clearsessions")

    log = log_de(resultado, "clearsessions")
    linhas = log.splitlines()
    assert re.fullmatch(
        r"\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\] início: clearsessions", linhas[0]
    )
    assert "saida-do-comando" in linhas
    assert re.fullmatch(r"\[.+Z\] fim: status 0", linhas[-1])


@precisa_de_sh
def test_log_acumula_as_execucoes(rodar):
    rodar("clearsessions")
    resultado = rodar("clearsessions")

    assert log_de(resultado, "clearsessions").count("início: clearsessions") == 2


@precisa_de_sh
def test_falha_do_comando_vai_para_o_log_e_para_o_status(rodar):
    resultado = rodar("ler_cardapio", falha=3)

    assert resultado.returncode == 3
    assert log_de(resultado, "ler_cardapio").splitlines()[-1].endswith("fim: status 3")


@precisa_de_sh
@pytest.mark.parametrize(
    "nome", ["", "Clear", "clear sessions", "../x", "x;id", "-h", "x$(id)"]
)
def test_nome_de_comando_invalido_nao_chega_ao_docker(rodar, nome):
    resultado = rodar(nome)

    assert resultado.returncode == 2
    assert resultado.docker is None
    assert "comando inválido" in resultado.stderr


@precisa_de_sh
def test_sem_comando_mostra_o_uso(rodar):
    resultado = rodar()

    assert resultado.returncode == 2
    assert resultado.docker is None
    assert "uso:" in resultado.stderr


@precisa_de_sh
def test_argumentos_extras_sao_repassados(rodar):
    """Para rodar à mão com uma opção do comando (`--verbosity 2`, por
    exemplo); o cron não passa argumentos."""
    resultado = rodar("clearsessions", "--verbosity", "2")

    assert resultado.docker[-3:] == ["clearsessions", "--verbosity", "2"]


@pytest.mark.skipif(
    SH is None or shutil.which("flock") is None, reason="sem sh ou flock no PATH"
)
def test_segunda_execucao_simultanea_e_pulada(rodar, tmp_path):
    """O `ler_cardapio` pode demorar mais que o intervalo do cron; a segunda
    execução não roda por cima da primeira."""
    primeira = rodar("ler_cardapio", espera=3, fundo=True)
    try:
        trava = tmp_path / "logs" / "ler_cardapio.lock"
        for _ in range(50):
            if trava.exists():
                break
            subprocess.run([SH, "-c", "sleep 0.1"], check=False)
        resultado = rodar("ler_cardapio")
    finally:
        primeira.wait(timeout=10)

    assert resultado.returncode == 75
    assert "pulado: a execução anterior ainda está rodando" in log_de(
        resultado, "ler_cardapio"
    )
