#!/bin/bash
# Deploy automático do Bandejão na VM de produção (CD). Recebe o commit da
# `main` que passou no CI e põe esse commit no ar. Instalação e uso em
# docs/deploy/deploy-producao.md, "Deploy automático (CD)".
#
# Quem chama é o workflow .github/workflows/deploy.yml, pelo SSH, com uma
# chave que só pode rodar este script (command= no authorized_keys): o commit
# chega no SSH_ORIGINAL_COMMAND. À mão, como azureuser (nunca com sudo):
#
#   bandejao-deploy <commit de 40 caracteres>
#
# Roda a cópia instalada em /usr/local/bin, e não a do repositório: o
# `git merge` abaixo pode trocar o arquivo do repositório, e o bash lê o
# script aos poucos, enquanto roda.
#
# Passos: trava contra deploy duplo, confere a pasta e o commit, faz o backup
# do banco, avança a `main` até o commit (só fast-forward), sobe o Compose com
# --build e espera os serviços ficarem prontos, e confere a API pela internet.
# As migrations rodam na subida do backend (entrypoint.sh), por isso o backup
# vem antes. Não há rollback automático: se algo falhar, o log mostra o
# commit anterior e o backup para voltar à mão.
#
# É bash, e não sh como o rodar-comando.sh, por causa do pipefail: o status
# do mysqldump e do script não pode ser perdido no pipe do gzip e do tee.
#
# Status: 0 (no ar, ou um commit mais novo já estava no ar), 1 (falha num
# passo, ver o log), 2 (uso ou commit inválido), 75 (outro deploy rodando).

set -uo pipefail

repo=${BANDEJAO_REPO:-/home/azureuser/2026-2-Bandejao-UnB}
logs=${BANDEJAO_LOGS:-/var/log/bandejao}
backups=${BANDEJAO_BACKUPS:-/home/azureuser/backups}
url=${BANDEJAO_URL:-https://bandejaounb.com.br}
branch=main
log=$logs/deploy.log
trava=$logs/deploy.lock

# Se a conexão SSH cair no meio do deploy, o script não pode morrer entre o
# merge e o Compose: ignora o HUP e o PIPE (o docker herda), e o `tee -p`
# continua gravando no log mesmo sem ninguém lendo a saída.
trap '' HUP PIPE

agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
msg() { echo "[$(agora)] $*"; }

sha=${1:-${SSH_ORIGINAL_COMMAND:-}}
if [[ ! $sha =~ ^[0-9a-f]{40}$ ]]; then
    echo "uso: bandejao-deploy <commit de 40 caracteres>" >&2
    exit 2
fi

if ! mkdir -p "$logs" 2>/dev/null || ! (: >>"$log") 2>/dev/null; then
    echo "sem permissão de escrita em $log (o script rodou com sudo?)" >&2
    exit 1
fi

corpo() {
    msg "início: deploy de $sha"

    if ! cd "$repo"; then
        msg "ERRO: pasta $repo não encontrada"
        return 1
    fi
    local atual
    atual=$(git symbolic-ref --short -q HEAD)
    if [[ $atual != "$branch" ]]; then
        msg "ERRO: a VM está na branch '${atual:-(nenhuma)}', e o deploy automático é da '$branch' (git switch $branch)"
        return 1
    fi
    # Mudança feita à mão nos arquivos versionados se perderia, ou travaria o
    # merge. O .env e o .env.db não contam: estão no .gitignore.
    if [[ -n $(git status --porcelain --untracked-files=no) ]]; then
        msg "ERRO: há mudanças locais no repositório da VM (git status); o deploy não mexe nelas"
        return 1
    fi

    if ! git fetch --quiet origin "$branch"; then
        msg "ERRO: git fetch falhou"
        return 1
    fi
    if ! git merge-base --is-ancestor "$sha" "origin/$branch" 2>/dev/null; then
        msg "ERRO: o commit $sha não está na origin/$branch"
        return 1
    fi
    local anterior
    anterior=$(git rev-parse HEAD)
    # Um deploy atrasado (de um commit mais antigo que o atual) não pode
    # voltar o site. O mesmo commit passa: é o "Re-run" do workflow.
    if [[ $sha != "$anterior" ]] && git merge-base --is-ancestor "$sha" "$anterior"; then
        msg "pulado: o commit no ar ($anterior) já é mais novo que $sha"
        return 0
    fi

    # Backup antes de tudo: as migrations novas rodam na subida do backend.
    # Ficam os 10 mais recentes. O backup diário é outra tarefa (BD-15).
    local backup
    backup=$backups/deploy-$(date -u '+%Y-%m-%d-%H%M%S')-${sha:0:7}.sql.gz
    if ! (umask 077 && mkdir -p "$backups" &&
        docker compose exec -T db sh -c \
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --all-databases --single-transaction --routines --events --triggers' |
        gzip >"$backup"); then
        rm -f -- "$backup"
        msg "ERRO: o backup do banco falhou; nada foi mudado"
        return 1
    fi
    msg "backup: $backup ($(du -h "$backup" | cut -f1))"
    ls -1t "$backups"/deploy-*.sql.gz | tail -n +11 | xargs -r rm -f --

    if ! git merge --quiet --ff-only "$sha"; then
        msg "ERRO: git merge --ff-only falhou; nada foi mudado"
        return 1
    fi
    msg "código: $anterior -> $sha"

    local voltar="para voltar: git reset --hard $anterior && docker compose up -d --build (se uma migration nova já rodou, restaure também o $backup)"
    if ! docker compose up -d --build --wait --wait-timeout 600; then
        msg "ERRO: docker compose up falhou (docker compose ps; docker compose logs --tail 100 backend)"
        msg "$voltar"
        return 1
    fi
    if ! curl -fsS --max-time 15 --retry 5 --retry-delay 5 --retry-all-errors \
        -o /dev/null "$url/api/campi/"; then
        msg "ERRO: $url/api/campi/ não respondeu 200 depois do deploy"
        msg "$voltar"
        return 1
    fi
    # Só as imagens sem nome, que cada --build deixa para trás e enchem o disco.
    docker image prune -f >/dev/null || true

    # Estes arquivos ficam instalados fora do repositório: o merge não os
    # atualiza.
    if ! git diff --quiet "$anterior" "$sha" -- deploy/cron/bandejao deploy/cron/logrotate; then
        msg "AVISO: deploy/cron mudou; reinstale como em \"Tarefas periódicas\" no guia"
    fi
    if ! git diff --quiet "$anterior" "$sha" -- deploy/cd/deploy.sh; then
        msg "AVISO: deploy/cd/deploy.sh mudou; reinstale o /usr/local/bin/bandejao-deploy"
    fi

    msg "fim: $sha no ar"
}

# A trava fica no descritor 9, como no rodar-comando.sh.
exec 9>>"$trava"
if ! flock -n 9; then
    msg "pulado: outro deploy ainda está rodando" | tee -p -a "$log"
    exit 75
fi

corpo 2>&1 | tee -p -a "$log"
status=${PIPESTATUS[0]}
if [[ $status -ne 0 ]]; then
    logger -t bandejao-deploy -p user.err -- "deploy de $sha falhou (ver $log)" 2>/dev/null || true
fi
exit "$status"
