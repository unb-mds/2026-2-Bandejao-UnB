"""Deploy automático na VM de produção (CD, #240).

O workflow `.github/workflows/deploy.yml` espera o CI do commit da `main` e
chama, pelo SSH, o `deploy/cd/deploy.sh` (instalado na VM como
`/usr/local/bin/bandejao-deploy`). O workflow é lido como texto; o script
roda contra repositórios git de verdade (uma `origin` e o clone "da VM"), com
um `docker`, um `curl` e um `logger` falsos no PATH, que só gravam o que
receberam.
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "deploy" / "cd" / "deploy.sh"
WORKFLOW = RAIZ / ".github" / "workflows" / "deploy.yml"

# --- .github/workflows/deploy.yml -------------------------------------------


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
    texto = WORKFLOW.read_text(encoding="utf-8")
    blocos = re.findall(r"run: \|\n((?:\s{10,}.*\n|\n)+)", texto)
    assert blocos
    for bloco in blocos:
        assert "${{" not in bloco


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


# --- deploy/cd/deploy.sh com docker, curl e logger falsos -------------------

FERRAMENTAS = ("bash", "git", "flock", "timeout", "gzip")
falta = [nome for nome in FERRAMENTAS if shutil.which(nome) is None]
script = pytest.mark.skipif(bool(falta), reason=f"sem {', '.join(falta)} no PATH")

DOCKER_FALSO = """#!/bin/sh
printf '%s\\n' "$*" >> "$SAIDA_DOCKER"
case "$*" in
    *mysqldump*) echo "-- dump"; exit "${FALHA_BACKUP:-0}" ;;
    *" up "*)
        if [ -n "${ESPERA_UP:-}" ]; then exec sleep "$ESPERA_UP"; fi
        exit "${FALHA_UP:-0}" ;;
    *"caddy reload"*) exit "${FALHA_RELOAD:-0}" ;;
    *"image prune"*) exit "${FALHA_PRUNE:-0}" ;;
esac
exit 0
"""

CURL_FALSO = """#!/bin/sh
for ultimo in "$@"; do :; done
printf '%s\\n' "$ultimo" >> "$SAIDA_CURL"
case "$ultimo" in
    */api/campi/) printf '%s' "${CODIGO_API:-200}" ;;
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
    "FALHA_RELOAD",
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

    def rodar(self, *argumentos, **extra):
        env = {k: v for k, v in os.environ.items() if k not in VARIAVEIS_DOS_FALSOS}
        env.update(
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            SAIDA_DOCKER=str(self.saida_docker),
            SAIDA_CURL=str(self.saida_curl),
            SAIDA_LOGGER=str(self.saida_logger),
            BANDEJAO_REPO=str(self.vm),
            BANDEJAO_LOGS=str(self.logs),
            BANDEJAO_BACKUPS=str(self.backups),
            BANDEJAO_URL="https://exemplo.test",
            BANDEJAO_ESPERA_HTTP="0",
        )
        env.update({k: str(v) for k, v in extra.items()})
        resultado = subprocess.run(
            ["bash", str(SCRIPT), *argumentos],
            check=False,  # o status de saída é conferido pelos testes
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
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
    assert chamou(resultado, "mysqldump")
    assert chamou(resultado, "up -d --build --wait --wait-timeout 600")
    assert chamou(resultado, "image prune -f")
    assert not chamou(resultado, "caddy reload")
    assert resultado.curl == [
        "https://exemplo.test/",
        "https://exemplo.test/api/campi/",
    ]
    assert f"fim: {novo} no ar" in resultado.log
    [backup] = amb.backups_de_deploy()
    assert backup.name.endswith(f"-{novo[:7]}.sql.gz")
    assert (amb.backups / "ultimo-ok.sql.gz").samefile(backup)
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


@script
def test_caddyfile_alterado_recarrega_o_caddy(amb):
    resultado = amb.rodar(amb.publicar({"Caddyfile": "site { encode }\n"}))
    assert resultado.returncode == 0, resultado.log
    assert chamou(resultado, "exec -T caddy caddy reload --config /etc/caddy/Caddyfile")
    assert "Caddy recarregado" in resultado.log


@script
def test_reload_do_caddy_que_falha_e_erro(amb):
    resultado = amb.rodar(
        amb.publicar({"Caddyfile": "site { encode }\n"}), FALHA_RELOAD=1
    )
    assert resultado.returncode == 1
    assert "o reload do Caddy (Caddyfile novo) falhou" in resultado.log
    assert "para voltar:" in resultado.log


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
    segurando = subprocess.Popen(["flock", str(trava), "sleep", "30"])
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
        segurando.kill()
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
