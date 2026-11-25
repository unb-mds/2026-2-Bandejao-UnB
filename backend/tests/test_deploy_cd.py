"""Deploy automático na VM de produção (CD, #240).

O workflow `.github/workflows/deploy.yml` espera o CI do commit da `main` e
chama, pelo SSH, o `deploy/cd/deploy.sh` (instalado na VM como
`/usr/local/bin/bandejao-deploy`). O workflow é lido como YAML, e a espera
pelo CI roda no bash com um `gh` falso; o script roda contra repositórios git
de verdade (uma `origin` e o clone "da VM"), com um `docker`, um `curl` e um
`logger` falsos no PATH, que só gravam o que receberam.
"""

import os
import re
import shutil
import signal
import stat
import subprocess
import time
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "deploy" / "cd" / "deploy.sh"
WORKFLOW = RAIZ / ".github" / "workflows" / "deploy.yml"

# --- .github/workflows/deploy.yml -------------------------------------------


def passos_do_workflow():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["deploy"]["steps"]


def run_do_passo(nome):
    [passo] = [p for p in passos_do_workflow() if p.get("name") == nome]
    return passo["run"]


def test_workflow_so_dispara_em_push_na_main():
    texto = WORKFLOW.read_text(encoding="utf-8")
    gatilho = re.search(r"^on:\n(.*?)^\S", texto, re.MULTILINE | re.DOTALL)
    assert gatilho
    assert re.fullmatch(r'\s*push:\n\s*branches: \[ "main" \]\s*', gatilho.group(1)), (
        gatilho.group(1)
    )


def test_workflow_usa_o_environment_e_espera_os_dois_ci():
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^\s*name: producao$", texto, re.MULTILINE)
    assert '"Backend CI" "Frontend CI"' in texto
    assert "--branch main" in texto


def test_workflow_nao_interpola_expressoes_dentro_do_run():
    """`${{ }}` dentro de `run:` vira código do shell; os valores entram por
    `env:`."""
    blocos = [p["run"] for p in passos_do_workflow() if "run" in p]
    assert len(blocos) == 3
    for bloco in blocos:
        assert "${{" not in bloco


def test_workflow_nao_cancela_deploy_em_andamento():
    """Cancelar no meio deixaria a VM entre o código novo e o Compose antigo."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["concurrency"] == {
        "group": "deploy-producao",
        "cancel-in-progress": False,
    }


def test_workflow_le_host_e_usuario_das_variables():
    """O environment tem `DEPLOY_HOST` e `DEPLOY_USER` em Variables, e não em
    Secrets; ler de `secrets.` daria um destino vazio (`@`)."""
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert "${{ vars.DEPLOY_USER }}@${{ vars.DEPLOY_HOST }}" in texto
    assert "secrets.DEPLOY_HOST" not in texto
    assert "secrets.DEPLOY_USER" not in texto


def test_workflow_fixa_a_chave_do_servidor():
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert "StrictHostKeyChecking=yes" in texto
    comandos = [l for l in texto.splitlines() if not l.strip().startswith("#")]
    assert not any("ssh-keyscan" in l for l in comandos)


# A espera pelo CI é a única barreira contra deploy com o CI vermelho. Roda
# como no Actions (bash -eo pipefail), com um `gh` que devolve uma resposta
# por chamada (Backend CI e Frontend CI se alternam) e um `sleep` que não
# espera. "ERRO" é uma falha do `gh`; sem respostas, o `gh` também falha.
GH_FALSO = """#!/bin/sh
printf '%s\\n' "$*" >> "$CHAMADAS_GH"
resposta=$(head -n 1 "$RESPOSTAS_GH")
tail -n +2 "$RESPOSTAS_GH" > "$RESPOSTAS_GH.resto"
mv "$RESPOSTAS_GH.resto" "$RESPOSTAS_GH"
case "$resposta" in
    '' | ERRO) echo "erro da API" >&2; exit 1 ;;
esac
echo "$resposta"
"""

precisa_de_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="sem bash no PATH"
)


@pytest.fixture
def esperar_ci(tmp_path):
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    for nome, conteudo in (("gh", GH_FALSO), ("sleep", "#!/bin/sh\nexit 0\n")):
        arquivo = bin_falso / nome
        arquivo.write_text(conteudo, encoding="utf-8", newline="\n")
        arquivo.chmod(0o755)
    codigo = run_do_passo("Esperar o CI do commit")

    def esperar(*respostas):
        (tmp_path / "respostas").write_text(
            "".join(f"{r}\n" for r in respostas), encoding="utf-8"
        )
        chamadas = tmp_path / "chamadas"
        chamadas.unlink(missing_ok=True)
        resultado = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", codigo],
            check=False,  # o status de saída é conferido pelos testes
            env={
                **os.environ,
                "PATH": str(bin_falso) + os.pathsep + os.environ["PATH"],
                "RESPOSTAS_GH": str(tmp_path / "respostas"),
                "CHAMADAS_GH": str(chamadas),
                "GITHUB_REPOSITORY": "unb-mds/2026-2-Bandejao-UnB",
                "GITHUB_SHA": "a" * 40,
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        resultado.chamadas = ler_linhas(chamadas)
        return resultado

    return esperar


@precisa_de_bash
def test_espera_ci_os_dois_verdes(esperar_ci):
    resultado = esperar_ci("completed success", "completed success")
    assert resultado.returncode == 0, resultado.stdout
    assert len(resultado.chamadas) == 2
    for chamada, wf in zip(resultado.chamadas, ("Backend CI", "Frontend CI")):
        assert f"--workflow {wf} " in chamada
        assert f"--branch main --commit {'a' * 40} --event push" in chamada


@precisa_de_bash
@pytest.mark.parametrize(
    ("respostas", "mensagem"),
    [
        (["completed failure"], "Backend CI terminou com 'failure'"),
        (
            ["completed success", "completed cancelled"],
            "Frontend CI terminou com 'cancelled'",
        ),
    ],
)
def test_espera_ci_vermelho_nao_faz_deploy(esperar_ci, respostas, mensagem):
    resultado = esperar_ci(*respostas)
    assert resultado.returncode == 1
    assert f"::error::{mensagem}" in resultado.stdout


@precisa_de_bash
@pytest.mark.parametrize("pendente", ["null null", "in_progress null", "queued null"])
def test_espera_ci_pendente_espera_e_confere_de_novo(esperar_ci, pendente):
    resultado = esperar_ci(
        pendente, "completed success", "completed success", "completed success"
    )
    assert resultado.returncode == 0, resultado.stdout
    assert len(resultado.chamadas) == 4


@precisa_de_bash
def test_espera_ci_erro_do_gh_vira_pendente(esperar_ci):
    resultado = esperar_ci(
        "ERRO", "completed success", "completed success", "completed success"
    )
    assert resultado.returncode == 0, resultado.stdout
    assert "::warning::gh run list falhou para Backend CI" in resultado.stdout


@precisa_de_bash
def test_espera_ci_cinco_erros_seguidos_do_gh_param(esperar_ci):
    resultado = esperar_ci()  # sem respostas: o gh sempre falha
    assert resultado.returncode == 1
    assert "falhou 5 vezes seguidas para Backend CI" in resultado.stdout
    # Um contador por workflow: Backend, Frontend, ..., e o 5º do Backend.
    assert len(resultado.chamadas) == 9


@precisa_de_bash
def test_espera_ci_erros_de_um_so_workflow_tambem_param(esperar_ci):
    """Um sucesso do Frontend CI não zera o contador do Backend CI."""
    resultado = esperar_ci(*["ERRO", "completed success"] * 5)
    assert resultado.returncode == 1
    assert "falhou 5 vezes seguidas para Backend CI" in resultado.stdout
    assert len(resultado.chamadas) == 9


@precisa_de_bash
def test_espera_ci_sucesso_zera_o_contador_do_workflow(esperar_ci):
    """4 erros, um sucesso e mais 4 erros no Backend CI não somam 5 seguidos."""
    pendente = "null null"
    respostas = (
        ["ERRO", pendente] * 4
        + ["in_progress null", pendente]
        + ["ERRO", pendente] * 4
        + ["completed success", "completed success"]
    )
    resultado = esperar_ci(*respostas)
    assert resultado.returncode == 0, resultado.stdout
    assert len(resultado.chamadas) == len(respostas)


def test_espera_pelo_ci_vem_antes_do_deploy_e_sem_escape():
    """Um `if:` ou um `continue-on-error` na espera faria deploy com o CI
    vermelho."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["deploy"]
    nomes = [p.get("name") for p in job["steps"]]
    assert nomes == ["Esperar o CI do commit", "Deploy na VM", "Apagar a chave"]
    assert "continue-on-error" not in job
    assert "if" not in job
    for passo in job["steps"][:2]:
        assert "continue-on-error" not in passo
        assert "if" not in passo
    assert job["steps"][2]["if"] == "always()"


# --- deploy/cd/deploy.sh com docker, curl e logger falsos -------------------

FERRAMENTAS = ("bash", "git", "flock", "timeout", "gzip")
falta = [nome for nome in FERRAMENTAS if shutil.which(nome) is None]
script = pytest.mark.skipif(bool(falta), reason=f"sem {', '.join(falta)} no PATH")

DOCKER_FALSO = """#!/bin/sh
printf '%s\\n' "$*" >> "$SAIDA_DOCKER"
case "$*" in
    *mysqldump*) echo "-- dump"; exit "${FALHA_BACKUP:-0}" ;;
    *"--force-recreate caddy"*)
        # Recriado, o Caddy passa a ver o Caddyfile do repositório, a não ser
        # que fique preso ao arquivo antigo ($CADDY_PRESO).
        if [ -z "${FALHA_RECRIAR_CADDY:-}" ] && [ -z "${CADDY_PRESO:-}" ]; then
            cp Caddyfile "$CADDY_VISTO"
        fi
        exit "${FALHA_RECRIAR_CADDY:-0}" ;;
    *"caddy cat /etc/caddy/Caddyfile"*)
        # O que o container vê: fica em $CADDY_VISTO entre as execuções.
        if [ -n "${CADDY_FORA:-}" ]; then echo "service caddy is not running" >&2; exit 1; fi
        cat "$CADDY_VISTO" ;;
    *" up "*)
        if [ -n "${ESPERA_UP:-}" ]; then exec sleep "$ESPERA_UP"; fi
        exit "${FALHA_UP:-0}" ;;
    *"image prune"*) exit "${FALHA_PRUNE:-0}" ;;
esac
exit 0
"""

CURL_FALSO = """#!/bin/sh
for ultimo in "$@"; do :; done
printf '%s\\n' "$ultimo" >> "$SAIDA_CURL"
case "$ultimo" in
    */api/campi/)
        if [ -n "${CODIGOS_API:-}" ]; then
            # Um código por chamada, na ordem de $CODIGOS_API.
            n=$(grep -c 'api/campi/' "$SAIDA_CURL")
            codigo=$(echo "$CODIGOS_API" | cut -d' ' -f"$n")
            printf '%s' "${codigo:-200}"
        else
            printf '%s' "${CODIGO_API:-200}"
        fi ;;
    *) printf '%s' "${CODIGO_RAIZ:-200}" ;;
esac
"""

LOGGER_FALSO = """#!/bin/sh
printf '%s\\n' "$*" >> "$SAIDA_LOGGER"
"""

VARIAVEIS_DOS_FALSOS = (
    "FALHA_BACKUP",
    "ESPERA_UP",
    "FALHA_UP",
    "FALHA_RECRIAR_CADDY",
    "CADDY_PRESO",
    "CADDY_FORA",
    "FALHA_MERGE_BASE_NA",
    "CODIGOS_API",
    "FALHA_PRUNE",
    "CODIGO_API",
    "CODIGO_RAIZ",
    "SSH_ORIGINAL_COMMAND",
)


def git(pasta, *argumentos):
    return subprocess.run(
        ["git", "-C", str(pasta), *argumentos],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class Ambiente:
    """Uma `origin` com a `main`, o clone "da VM" e um clone de trabalho,
    que publica commits novos na `origin`."""

    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        for nome, conteudo in (
            ("docker", DOCKER_FALSO),
            ("curl", CURL_FALSO),
            ("logger", LOGGER_FALSO),
        ):
            arquivo = self.bin / nome
            arquivo.write_text(conteudo, encoding="utf-8", newline="\n")
            arquivo.chmod(0o755)
        self.logs = tmp_path / "logs"
        self.backups = tmp_path / "backups"
        self.saida_docker = tmp_path / "docker.txt"
        self.saida_curl = tmp_path / "curl.txt"
        self.saida_logger = tmp_path / "logger.txt"
        self.caddy_visto = tmp_path / "caddy_visto"
        self.caddy_visto.write_text("site {}\n", encoding="utf-8")

        self.origin = tmp_path / "origin.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True
        )
        self.trabalho = tmp_path / "trabalho"
        subprocess.run(
            ["git", "clone", "-q", str(self.origin), str(self.trabalho)],
            check=True,
            capture_output=True,
        )
        self.configurar(self.trabalho)
        git(self.trabalho, "checkout", "-q", "-b", "main")
        self.publicados = 0
        self.inicial = self.publicar({"Caddyfile": "site {}\n", "README.md": "1\n"})
        self.vm = tmp_path / "vm"
        subprocess.run(
            ["git", "clone", "-q", str(self.origin), str(self.vm)],
            check=True,
            capture_output=True,
        )
        self.configurar(self.vm)

    @staticmethod
    def configurar(pasta):
        git(pasta, "config", "user.email", "teste@example.com")
        git(pasta, "config", "user.name", "Teste")

    def publicar(self, arquivos=None):
        """Commita na `main` do clone de trabalho, faz o push e devolve o
        commit."""
        self.publicados += 1
        arquivos = arquivos or {"README.md": f"{self.publicados}\n"}
        for nome, conteudo in arquivos.items():
            caminho = self.trabalho / nome
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(conteudo, encoding="utf-8")
        git(self.trabalho, "add", "-A")
        git(self.trabalho, "commit", "-q", "-m", "commit")
        git(self.trabalho, "push", "-q", "origin", "main")
        return git(self.trabalho, "rev-parse", "HEAD")

    def head_da_vm(self):
        return git(self.vm, "rev-parse", "HEAD")

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in VARIAVEIS_DOS_FALSOS}
        env.update(
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            SAIDA_DOCKER=str(self.saida_docker),
            SAIDA_CURL=str(self.saida_curl),
            SAIDA_LOGGER=str(self.saida_logger),
            CADDY_VISTO=str(self.caddy_visto),
            BANDEJAO_REPO=str(self.vm),
            BANDEJAO_LOGS=str(self.logs),
            BANDEJAO_BACKUPS=str(self.backups),
            BANDEJAO_URL="https://exemplo.test",
            BANDEJAO_ESPERA_HTTP="0",
        )
        env.update({k: str(v) for k, v in extra.items()})
        return env

    def rodar(self, *argumentos, **extra):
        resultado = subprocess.run(
            ["bash", str(SCRIPT), *argumentos],
            check=False,  # o status de saída é conferido pelos testes
            env=self.env(**extra),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        return self.recolher(resultado)

    def recolher(self, resultado):
        resultado.docker = ler_linhas(self.saida_docker)
        resultado.curl = ler_linhas(self.saida_curl)
        resultado.logger = ler_linhas(self.saida_logger)
        resultado.log = (
            (self.logs / "deploy.log").read_text(encoding="utf-8")
            if (self.logs / "deploy.log").exists()
            else ""
        )
        for arquivo in (self.saida_docker, self.saida_curl, self.saida_logger):
            arquivo.unlink(missing_ok=True)
        return resultado

    def backups_de_deploy(self):
        return sorted(self.backups.glob("deploy-*.sql.gz"))


def ler_linhas(arquivo):
    return arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []


def chamou(resultado, trecho):
    return any(trecho in linha for linha in resultado.docker)


@pytest.fixture
def amb(tmp_path):
    return Ambiente(tmp_path)


@script
@pytest.mark.parametrize(
    "valor", ["", "abc", "E686520" + "0" * 33, "a" * 39, "a" * 41, "a" * 40 + ";id"]
)
def test_commit_invalido_nao_faz_nada(amb, valor):
    resultado = amb.rodar(valor)
    assert resultado.returncode == 2
    assert "uso:" in resultado.stderr
    assert resultado.docker == []


@script
def test_deploy_normal(amb):
    novo = amb.publicar()
    resultado = amb.rodar(novo)
    assert resultado.returncode == 0, resultado.log
    assert amb.head_da_vm() == novo
    # O mysqldump tem o próprio limite dentro do container.
    assert chamou(resultado, 'exec timeout "$1" mysqldump')
    assert chamou(resultado, "--triggers sh 14m")
    assert chamou(resultado, "up -d --build --wait --wait-timeout 600")
    assert chamou(resultado, "image prune -f")
    # O Caddy já vê o Caddyfile do repositório: é só conferido.
    assert chamou(resultado, "compose exec -T caddy cat /etc/caddy/Caddyfile")
    assert not chamou(resultado, "--force-recreate")
    assert resultado.curl == [
        "https://exemplo.test/",
        "https://exemplo.test/api/campi/",
    ]
    assert f"fim: {novo} no ar" in resultado.log
    [backup] = amb.backups_de_deploy()
    assert backup.name.endswith(f"-{novo[:7]}.sql.gz")
    assert (amb.backups / "ultimo-ok.sql.gz").samefile(backup)
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert stat.S_IMODE(amb.backups.stat().st_mode) == 0o700
    assert resultado.logger == []


@script
def test_commit_pelo_ssh_original_command(amb):
    novo = amb.publicar()
    resultado = amb.rodar(SSH_ORIGINAL_COMMAND=novo)
    assert resultado.returncode == 0, resultado.log
    assert amb.head_da_vm() == novo


@script
def test_backup_vem_antes_do_merge_e_do_compose(amb):
    novo = amb.publicar()
    resultado = amb.rodar(novo)
    passos = [l for l in resultado.docker if "mysqldump" in l or " up " in l]
    assert "mysqldump" in passos[0] and " up " in passos[1]
    assert resultado.log.index("backup:") < resultado.log.index("código:")


@script
def test_commit_atrasado_e_pulado(amb):
    antigo = amb.publicar()
    novo = amb.publicar()
    assert amb.rodar(novo).returncode == 0
    resultado = amb.rodar(antigo)
    assert resultado.returncode == 0
    assert "pulado: o commit no ar" in resultado.log
    assert amb.head_da_vm() == novo
    assert resultado.docker == []


@script
def test_mesmo_commit_de_novo_refaz_o_deploy(amb):
    """É o "Re-run" do workflow, e o primeiro deploy depois do `git switch
    main` na VM."""
    resultado = amb.rodar(amb.inicial)
    assert resultado.returncode == 0, resultado.log
    assert chamou(resultado, " up ")


@script
def test_commit_inexistente(amb):
    resultado = amb.rodar("0123456789abcdef0123456789abcdef01234567")
    assert resultado.returncode == 1
    assert "não existe na origin" in resultado.log
    assert resultado.docker == []
    assert any("falhou" in linha for linha in resultado.logger)


@script
def test_commit_fora_da_main(amb):
    git(amb.trabalho, "checkout", "-q", "-b", "outra")
    (amb.trabalho / "x.txt").write_text("x\n", encoding="utf-8")
    git(amb.trabalho, "add", "-A")
    git(amb.trabalho, "commit", "-q", "-m", "fora")
    git(amb.trabalho, "push", "-q", "origin", "outra")
    fora = git(amb.trabalho, "rev-parse", "HEAD")
    git(amb.vm, "fetch", "-q", "origin", "outra")
    resultado = amb.rodar(fora)
    assert resultado.returncode == 1
    assert "não está na origin/main" in resultado.log
    assert resultado.docker == []


@script
def test_vm_em_outra_branch(amb):
    git(amb.vm, "switch", "-q", "-c", "develop")
    resultado = amb.rodar(amb.publicar())
    assert resultado.returncode == 1
    assert "está na branch 'develop'" in resultado.log
    assert resultado.docker == []


@script
def test_mudanca_local_na_vm(amb):
    (amb.vm / "README.md").write_text("mexido\n", encoding="utf-8")
    resultado = amb.rodar(amb.publicar())
    assert resultado.returncode == 1
    assert "mudanças locais" in resultado.log
    assert resultado.docker == []


@script
def test_main_da_vm_divergente_para_antes_do_backup(amb):
    """Um commit feito na VM (ou um force-push na `main`) só apareceria no
    `merge --ff-only`, depois de um backup inútil."""
    (amb.vm / "local.txt").write_text("x\n", encoding="utf-8")
    git(amb.vm, "add", "-A")
    git(amb.vm, "commit", "-q", "-m", "na vm")
    resultado = amb.rodar(amb.publicar())
    assert resultado.returncode == 1
    assert "não é sucessor do commit da VM" in resultado.log
    assert resultado.docker == []
    assert amb.backups_de_deploy() == []


@script
def test_backup_que_falha_nao_muda_nada(amb):
    novo = amb.publicar()
    resultado = amb.rodar(novo, FALHA_BACKUP=1)
    assert resultado.returncode == 1
    assert "o backup do banco falhou" in resultado.log
    assert amb.head_da_vm() == amb.inicial
    assert not chamou(resultado, " up ")
    assert amb.backups_de_deploy() == []


@script
def test_compose_que_falha_mostra_como_voltar_e_nao_roda_a_rotacao(amb):
    novo = amb.publicar()
    resultado = amb.rodar(novo, FALHA_UP=1)
    assert resultado.returncode == 1
    assert "docker compose up falhou" in resultado.log
    assert f"git reset --hard {amb.inicial}" in resultado.log
    assert not (amb.backups / "ultimo-ok.sql.gz").exists()
    assert any("falhou" in linha for linha in resultado.logger)


@script
def test_tentativas_que_falham_nao_apagam_o_backup_de_antes_da_migration(amb):
    novo = amb.publicar()
    primeira = amb.rodar(novo, FALHA_UP=1)
    assert primeira.returncode == 1
    [antes_da_migration] = amb.backups_de_deploy()
    # Onze tentativas depois dela (com horários mais novos), já pós-migration.
    agora = time.time()
    for i in range(11):
        depois = amb.backups / f"deploy-2099-01-01-0000{i:02d}-{novo[:7]}.sql.gz"
        depois.write_bytes(b"")
        os.utime(depois, (agora + 60 + i, agora + 60 + i))
    assert amb.rodar(novo, FALHA_UP=1).returncode == 1
    assert antes_da_migration.exists()


@script
def test_rotacao_guarda_os_10_mais_recentes_e_o_ultimo_ok(amb):
    amb.backups.mkdir()
    for i in range(12):
        antigo = amb.backups / f"deploy-2026-01-{i + 1:02d}-000000-aaaaaaa.sql.gz"
        antigo.write_bytes(b"")
        os.utime(antigo, (1_700_000_000 + i, 1_700_000_000 + i))
    resultado = amb.rodar(amb.publicar())
    assert resultado.returncode == 0, resultado.log
    restantes = amb.backups_de_deploy()
    assert len(restantes) == 10
    assert not (amb.backups / "deploy-2026-01-01-000000-aaaaaaa.sql.gz").exists()
    assert (amb.backups / "ultimo-ok.sql.gz").exists()


@script
def test_passo_travado_tem_tempo_limite_e_libera_a_trava(amb):
    novo = amb.publicar()
    resultado = amb.rodar(novo, ESPERA_UP=60, BANDEJAO_LIMITE_COMPOSE="1s")
    assert resultado.returncode == 1
    assert "docker compose up passou do tempo limite (status 124)" in resultado.log
    # A trava foi liberada: o deploy seguinte roda.
    seguinte = amb.rodar(novo)
    assert seguinte.returncode == 0, seguinte.log


NOVO_CADDYFILE = {"Caddyfile": "site { encode }\n"}


@script
def test_caddyfile_alterado_recria_o_caddy_e_confere_o_conteudo(amb):
    """O bind mount de um arquivo só fica preso ao arquivo antigo: um `caddy
    reload` leria a configuração velha."""
    resultado = amb.rodar(amb.publicar(NOVO_CADDYFILE))
    assert resultado.returncode == 0, resultado.log
    assert chamou(resultado, "compose up -d --no-deps --force-recreate caddy")
    assert not chamou(resultado, "caddy reload")
    assert "Caddy recriado" in resultado.log
    assert amb.caddy_visto.read_text(encoding="utf-8") == NOVO_CADDYFILE["Caddyfile"]


@script
def test_re_run_depois_de_falha_ainda_recria_o_caddy(amb):
    """O deploy que mudou o Caddyfile falhou depois do merge; no "Re-run" o
    commit da VM já é o do deploy, e um `git diff` viria vazio."""
    novo = amb.publicar(NOVO_CADDYFILE)
    assert amb.rodar(novo, FALHA_UP=1).returncode == 1
    resultado = amb.rodar(novo)
    assert resultado.returncode == 0, resultado.log
    assert chamou(resultado, "--force-recreate caddy")
    assert amb.caddy_visto.read_text(encoding="utf-8") == NOVO_CADDYFILE["Caddyfile"]


@script
def test_recriacao_do_caddy_que_falha_e_erro(amb):
    resultado = amb.rodar(amb.publicar(NOVO_CADDYFILE), FALHA_RECRIAR_CADDY=1)
    assert resultado.returncode == 1
    assert "a recriação do Caddy falhou" in resultado.log
    assert "para voltar:" in resultado.log


@script
def test_caddy_que_ainda_ve_o_caddyfile_antigo_e_erro(amb):
    resultado = amb.rodar(amb.publicar(NOVO_CADDYFILE), CADDY_PRESO=1)
    assert resultado.returncode == 1
    assert "o Caddy recriado ainda não vê o Caddyfile do repositório" in resultado.log
    assert not (amb.backups / "ultimo-ok.sql.gz").exists()


@script
def test_caddy_fora_do_ar_aponta_os_logs(amb):
    """Um Caddyfile com erro de sintaxe deixa o Caddy em loop de restart: o
    `exec` falha, e isso não é "vê o arquivo antigo"."""
    resultado = amb.rodar(amb.publicar(NOVO_CADDYFILE), CADDY_FORA=1)
    assert resultado.returncode == 1
    assert "o Caddy não está no ar depois de recriado" in resultado.log
    assert "docker compose logs --tail 50 caddy" in resultado.log


@script
def test_health_check_tenta_de_novo_ate_o_200(amb):
    """Os segundos do Caddy recém-recriado (ou do Gunicorn subindo)."""
    resultado = amb.rodar(amb.publicar(), CODIGOS_API="502 000 200")
    assert resultado.returncode == 0, resultado.log
    assert resultado.curl.count("https://exemplo.test/api/campi/") == 3


@script
@pytest.mark.parametrize(
    ("variavel", "endereco"),
    [
        ("CODIGO_RAIZ", "https://exemplo.test/"),
        ("CODIGO_API", "https://exemplo.test/api/campi/"),
    ],
)
@pytest.mark.parametrize("codigo", ["301", "502", "000"])
def test_pwa_ou_api_sem_200_e_erro(amb, variavel, endereco, codigo):
    resultado = amb.rodar(amb.publicar(), **{variavel: codigo})
    assert resultado.returncode == 1
    assert f"{endereco} respondeu {codigo}, e não 200" in resultado.log
    assert not (amb.backups / "ultimo-ok.sql.gz").exists()


@script
def test_backups_acumulados_viram_aviso(amb):
    amb.backups.mkdir()
    for i in range(20):
        (amb.backups / f"deploy-2026-01-01-0000{i:02d}-aaaaaaa.sql.gz").write_bytes(b"")
    resultado = amb.rodar(amb.publicar(), FALHA_UP=1)
    assert "AVISO: 21 backups de deploy" in resultado.log


@script
def test_ate_20_backups_acumulados_nao_avisa(amb):
    amb.backups.mkdir()
    for i in range(19):
        (amb.backups / f"deploy-2026-01-01-0000{i:02d}-aaaaaaa.sql.gz").write_bytes(b"")
    resultado = amb.rodar(amb.publicar(), FALHA_UP=1)
    assert "backups de deploy em" not in resultado.log


@script
def test_limite_do_mysqldump_e_um_minuto_menor_que_o_do_backup(amb):
    resultado = amb.rodar(amb.publicar(), BANDEJAO_LIMITE_BACKUP_MIN=5)
    assert resultado.returncode == 0, resultado.log
    assert chamou(resultado, "--triggers sh 4m")


@script
@pytest.mark.parametrize("valor", ["1", "0", "15m", "abc", "-3"])
def test_limite_do_backup_invalido_nao_faz_nada(amb, valor):
    resultado = amb.rodar(amb.publicar(), BANDEJAO_LIMITE_BACKUP_MIN=valor)
    assert resultado.returncode == 2
    assert "BANDEJAO_LIMITE_BACKUP_MIN" in resultado.stderr
    assert resultado.docker == []


@script
def test_prune_que_falha_so_avisa(amb):
    resultado = amb.rodar(amb.publicar(), FALHA_PRUNE=1)
    assert resultado.returncode == 0
    assert "AVISO: docker image prune falhou" in resultado.log


@script
@pytest.mark.parametrize(
    ("arquivo", "aviso"),
    [
        ("deploy/cron/bandejao", "deploy/cron mudou"),
        ("deploy/cd/deploy.sh", "deploy/cd/deploy.sh mudou"),
    ],
)
def test_avisa_quando_arquivo_instalado_fora_do_repo_muda(amb, arquivo, aviso):
    resultado = amb.rodar(amb.publicar({arquivo: "novo\n"}))
    assert resultado.returncode == 0, resultado.log
    assert f"AVISO: {aviso}" in resultado.log


@script
def test_outro_deploy_rodando_e_pulado(amb):
    amb.logs.mkdir()
    trava = amb.logs / "deploy.lock"
    novo = amb.publicar()
    # Numa sessão própria, para matar o flock e o sleep juntos no fim.
    segurando = subprocess.Popen(
        ["flock", str(trava), "sleep", "30"], start_new_session=True
    )
    try:
        # Espera o flock de fora pegar a trava.
        for _ in range(100):
            if (
                subprocess.run(
                    ["flock", "-n", str(trava), "true"], check=False
                ).returncode
                == 1
            ):
                break
            time.sleep(0.05)
        resultado = amb.rodar(novo)
    finally:
        os.killpg(segurando.pid, signal.SIGKILL)
        segurando.wait()
    assert resultado.returncode == 75
    assert "outro deploy ainda está rodando" in resultado.log
    assert any("pulado" in linha for linha in resultado.logger)
    assert resultado.docker == []


@script
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="o root escreve em tudo"
)
@pytest.mark.parametrize("nome", ["deploy.log", "deploy.lock"])
def test_log_ou_trava_sem_escrita_nao_vira_outro_deploy_rodando(amb, nome):
    amb.logs.mkdir()
    arquivo = amb.logs / nome
    arquivo.write_text("", encoding="utf-8")
    arquivo.chmod(0o444)
    resultado = amb.rodar(amb.publicar())
    assert resultado.returncode == 73
    assert "sem permissão de escrita" in resultado.stderr
    assert resultado.docker == []


@script
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="o root escreve em tudo"
)
def test_pasta_de_log_que_nao_pode_ser_criada_sai_com_73(amb, tmp_path):
    bloqueada = tmp_path / "bloqueada"
    bloqueada.mkdir()
    bloqueada.chmod(0o555)
    try:
        resultado = amb.rodar(amb.publicar(), BANDEJAO_LOGS=str(bloqueada / "logs"))
    finally:
        bloqueada.chmod(0o755)
    assert resultado.returncode == 73
    assert "não foi possível criar" in resultado.stderr
    assert resultado.docker == []


@script
def test_conexao_que_cai_no_meio_nao_interrompe_o_deploy(amb):
    """Se o SSH cair durante o `docker compose up`, o script e o `tee`
    recebem HUP (o docker, não: o `timeout` o põe noutro grupo de processos),
    e a saída fica sem ninguém lendo. O deploy tem que ir até o fim (o
    `trap '' HUP PIPE` e o `tee -p`), e não parar entre o código novo e o
    Compose antigo."""
    novo = amb.publicar()
    processo = subprocess.Popen(
        ["bash", str(SCRIPT), novo],
        env=amb.env(ESPERA_UP=2),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        for _ in range(200):
            if any(" up " in linha for linha in ler_linhas(amb.saida_docker)):
                break
            time.sleep(0.05)
        else:
            pytest.fail("o deploy não chegou ao docker compose up")
        processo.stdout.close()
        os.killpg(processo.pid, signal.SIGHUP)
        status = processo.wait(timeout=60)
    finally:
        if processo.poll() is None:
            os.killpg(processo.pid, signal.SIGKILL)
    resultado = amb.recolher(subprocess.CompletedProcess(processo.args, status))
    assert status == 0, resultado.log
    assert amb.head_da_vm() == novo
    assert f"fim: {novo} no ar" in resultado.log


# `git merge-base --is-ancestor` sai com 128 num erro do git (objeto
# corrompido, por exemplo). Um `git` que repassa tudo ao de verdade, menos a
# N-ésima chamada do `merge-base`.
GIT_FALSO = """#!/bin/sh
if [ "$1" = merge-base ] && [ -n "${FALHA_MERGE_BASE_NA:-}" ]; then
    echo x >> "$SAIDA_DOCKER.merge-base"
    if [ "$(wc -l < "$SAIDA_DOCKER.merge-base")" -eq "$FALHA_MERGE_BASE_NA" ]; then
        echo "fatal: erro de teste" >&2
        exit 128
    fi
fi
exec "$GIT_DE_VERDADE" "$@"
"""


@script
@pytest.mark.parametrize(
    "chamada",
    [
        1,  # o commit está na origin/main?
        2,  # é mais antigo que o da VM ("pulado")?
        3,  # vem depois do commit da VM (fast-forward)?
    ],
)
def test_erro_do_merge_base_nao_vira_resposta(amb, chamada):
    """Na 2ª conferência, um erro que virasse "é ancestral" sairia com 0 sem
    fazer o deploy."""
    git_falso = amb.bin / "git"
    git_falso.write_text(GIT_FALSO, encoding="utf-8", newline="\n")
    git_falso.chmod(0o755)
    novo = amb.publicar()
    resultado = amb.rodar(
        novo, FALHA_MERGE_BASE_NA=chamada, GIT_DE_VERDADE=shutil.which("git")
    )
    assert resultado.returncode == 1
    assert "falhou (status 128)" in resultado.log
    assert "pulado" not in resultado.log
    assert "não está na origin/main" not in resultado.log
    assert "não é sucessor" not in resultado.log
    assert resultado.docker == []
    assert amb.head_da_vm() == amb.inicial
