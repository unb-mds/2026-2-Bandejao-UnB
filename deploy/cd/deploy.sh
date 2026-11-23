#!/bin/bash
# Deploy automático do Bandejão na VM de produção (CD, #240). Recebe o commit
# da `main` que passou no CI e põe esse commit no ar. Instalação e uso em
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
# --build e espera os serviços ficarem prontos, recria o Caddy se o
# Caddyfile mudou e confere o PWA e a API pela internet. As migrations rodam
# na subida do backend (entrypoint.sh), por isso o backup vem antes. Não há
# rollback automático: se algo falhar, o log mostra o commit anterior e o
# backup para voltar à mão.
#
# Backups: um por deploy, em $BANDEJAO_BACKUPS. A rotação (os 10 mais
# recentes) só roda depois de um deploy que deu certo: tentativas que falham
# depois de uma migration não apagam o backup de antes dela. O backup feito
# antes do último deploy que deu certo também fica em ultimo-ok.sql.gz, fora
# da rotação: é o banco de antes do deploy que está no ar. Para desfazer um
# deploy que acabou de falhar, o backup certo é o que o log desse deploy
# mostra. O backup diário é outra tarefa (BD-15).
#
# Cada passo que pode travar tem tempo limite: o HUP é ignorado (abaixo), e um
# passo travado seguraria a trava depois de o job do Actions morrer. Os
# limites podem ser trocados por $BANDEJAO_LIMITE_FETCH (padrão 2m),
# $BANDEJAO_LIMITE_BACKUP (15m, o cliente do docker; o mysqldump, dentro do
# container, tem 1 min a menos) e $BANDEJAO_LIMITE_COMPOSE (30m, o build e o
# --wait juntos). Somados aos fixos (Caddy 2m, prune 2m) e às conferências,
# o pior caso fica perto de 55 min: o step do workflow tem 70.
#
# É bash, e não sh como o rodar-comando.sh, por causa do pipefail: o status
# do mysqldump e do script não pode ser perdido no pipe do gzip e do tee.
#
# Status: 0 (no ar, ou um commit mais novo já estava no ar), 1 (falha num
# passo, ver o log), 2 (uso ou commit inválido), 73 (sem escrita na pasta de
# log, no log ou na trava), 75 (outro deploy rodando).

set -uo pipefail

repo=${BANDEJAO_REPO:-/home/azureuser/2026-2-Bandejao-UnB}
logs=${BANDEJAO_LOGS:-/var/log/bandejao}
backups=${BANDEJAO_BACKUPS:-/home/azureuser/backups}
url=${BANDEJAO_URL:-https://bandejaounb.com.br}
limite_fetch=${BANDEJAO_LIMITE_FETCH:-2m}
limite_backup=${BANDEJAO_LIMITE_BACKUP:-15m}
limite_compose=${BANDEJAO_LIMITE_COMPOSE:-30m}
limite_dump=${BANDEJAO_LIMITE_DUMP:-14m}
espera_http=${BANDEJAO_ESPERA_HTTP:-5}
branch=main
log=$logs/deploy.log
trava=$logs/deploy.lock
manter=10
# Acima disso, os backups de tentativas que falharam viram AVISO no log.
acumulados=20

# Se a conexão SSH cair no meio do deploy, o script não pode morrer entre o
# merge e o Compose: ignora o HUP e o PIPE (o docker herda), e o `tee -p`
# continua gravando no log mesmo sem ninguém lendo a saída.
trap '' HUP PIPE

agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
msg() { echo "[$(agora)] $*"; }

# Roda com tempo limite: TERM no fim do prazo e KILL 30 s depois.
limitado() {
    local prazo=$1
    shift
    timeout --kill-after=30s "$prazo" "$@"
}

# Mensagem de erro de um passo pelo status: 124 é o tempo limite do
# `timeout`; 137 é o KILL (do `timeout`, 30 s depois, ou de fora, como um
# `kill -9` ou a falta de memória).
falhou() {
    local status=$1 passo=$2
    case $status in
        124) msg "ERRO: $passo passou do tempo limite (status 124)" ;;
        137) msg "ERRO: $passo foi encerrado com KILL (status 137: tempo limite ou de fora)" ;;
        *) msg "ERRO: $passo falhou (status $status)" ;;
    esac
}

# `git merge-base --is-ancestor`: 0 (é ancestral), 1 (não é) ou erro do git
# (128, por exemplo), que não pode virar "não é ancestral".
ancestral() {
    git merge-base --is-ancestor "$1" "$2"
    local status=$?
    if [[ $status -gt 1 ]]; then
        msg "ERRO: git merge-base $1 $2 falhou (status $status)"
    fi
    return "$status"
}

# Espera um 200 da URL: um 3xx também é falha (o curl -f só falha com 400 ou
# mais). Até 6 tentativas, para dar tempo ao Caddy recém-recriado.
conferir_url() {
    local endereco=$1 codigo=''
    for _ in 1 2 3 4 5 6; do
        codigo=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$endereco")
        [[ $codigo == 200 ]] && return 0
        sleep "$espera_http"
    done
    msg "ERRO: $endereco respondeu ${codigo:-sem resposta}, e não 200"
    return 1
}

# Depois de um deploy que deu certo: o backup dele vira o ultimo-ok, e só
# ficam os $manter mais recentes. Uma falha aqui não desfaz o deploy, só avisa.
guardar_backups() {
    local backup=$1 antigos
    if ! ln -f -- "$backup" "$backups/ultimo-ok.sql.gz"; then
        msg "AVISO: não foi possível gravar $backups/ultimo-ok.sql.gz"
    fi
    if ! antigos=$(ls -1t -- "$backups"/deploy-*.sql.gz | tail -n +$((manter + 1))); then
        msg "AVISO: não foi possível listar os backups em $backups; nenhum foi apagado"
        return
    fi
    if [[ -n $antigos ]] && ! xargs -r -d '\n' rm -f -- <<<"$antigos"; then
        msg "AVISO: a rotação dos backups falhou (ls -l $backups)"
    fi
}

sha=${1:-${SSH_ORIGINAL_COMMAND:-}}
if [[ ! $sha =~ ^[0-9a-f]{40}$ ]]; then
    echo "uso: bandejao-deploy <commit de 40 caracteres>" >&2
    exit 2
fi

if ! mkdir -p "$logs" 2>/dev/null; then
    echo "não foi possível criar $logs (o script rodou com sudo?)" >&2
    logger -t bandejao-deploy -p user.err -- "não foi possível criar $logs" 2>/dev/null || true
    exit 73
fi
# O log e a trava são testados antes: um arquivo do root (o script rodou com
# sudo) faria o flock falhar como se houvesse outro deploy rodando.
for arquivo in "$log" "$trava"; do
    if ! (: >>"$arquivo") 2>/dev/null; then
        echo "sem permissão de escrita em $arquivo (o script rodou com sudo?)" >&2
        logger -t bandejao-deploy -p user.err -- "sem permissão de escrita em $arquivo" 2>/dev/null || true
        exit 73
    fi
done

corpo() {
    msg "início: deploy de $sha"

    if ! cd "$repo"; then
        msg "ERRO: pasta $repo não encontrada"
        return 1
    fi
    local atual
    atual=$(git symbolic-ref --short -q HEAD)
    if [[ $atual != "$branch" ]]; then
        msg "ERRO: a VM está na branch '${atual:-(nenhuma)}', e o deploy automático é da '$branch' (ver o passo 5 do guia)"
        return 1
    fi
    # Mudança feita à mão nos arquivos versionados se perderia, ou travaria o
    # merge. O .env e o .env.db não contam: estão no .gitignore.
    local mudancas
    if ! mudancas=$(git status --porcelain --untracked-files=no); then
        msg "ERRO: git status falhou"
        return 1
    fi
    if [[ -n $mudancas ]]; then
        msg "ERRO: há mudanças locais no repositório da VM (git status); o deploy não mexe nelas"
        return 1
    fi

    local status
    limitado "$limite_fetch" git fetch --quiet origin "$branch"
    status=$?
    if [[ $status -ne 0 ]]; then
        falhou "$status" "git fetch"
        return 1
    fi
    if ! git cat-file -e "$sha^{commit}" 2>/dev/null; then
        msg "ERRO: o commit $sha não existe na origin"
        return 1
    fi
    ancestral "$sha" "origin/$branch"
    case $? in
        0) ;;
        1)
            msg "ERRO: o commit $sha não está na origin/$branch"
            return 1
            ;;
        *) return 1 ;;
    esac
    local anterior
    anterior=$(git rev-parse HEAD)
    # Um deploy atrasado (de um commit mais antigo que o atual) não pode
    # voltar o site. O mesmo commit passa: é o "Re-run" do workflow.
    if [[ $sha != "$anterior" ]]; then
        ancestral "$sha" "$anterior"
        case $? in
            0)
                msg "pulado: o commit no ar ($anterior) já é mais novo que $sha"
                return 0
                ;;
            1) ;;
            *) return 1 ;;
        esac
    fi
    # Conferido antes do backup: um force-push na `main` ou um commit feito na
    # VM só apareceriam no `merge --ff-only`, depois de um backup inútil.
    ancestral "$anterior" "$sha"
    case $? in
        0) ;;
        1)
            msg "ERRO: $sha não é sucessor do commit da VM ($anterior): force-push na $branch ou commit feito na VM? (git log --oneline -3)"
            return 1
            ;;
        *) return 1 ;;
    esac

    # Backup antes de tudo: as migrations novas rodam na subida do backend.
    # O `docker exec` não repassa o sinal do `timeout` de fora ao processo do
    # container: o mysqldump tem o próprio limite lá dentro, um pouco menor,
    # para não continuar segurando o banco depois de o cliente morrer.
    local backup
    backup=$backups/deploy-$(date -u '+%Y-%m-%d-%H%M%S')-${sha:0:7}.sql.gz
    (umask 077 && mkdir -p "$backups" &&
        limitado "$limite_backup" docker compose exec -T db sh -c \
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec timeout "$1" mysqldump -uroot --all-databases --single-transaction --routines --events --triggers' \
            sh "$limite_dump" |
        gzip >"$backup")
    status=$?
    if [[ $status -ne 0 ]]; then
        rm -f -- "$backup"
        falhou "$status" "o backup do banco"
        msg "nada foi mudado; se o mysqldump ficou rodando: docker compose exec db pkill mysqldump"
        return 1
    fi
    msg "backup: $backup ($(du -h "$backup" | cut -f1))"
    local quantos
    quantos=$(find "$backups" -maxdepth 1 -name 'deploy-*.sql.gz' | wc -l)
    if [[ $quantos -gt $acumulados ]]; then
        msg "AVISO: $quantos backups de deploy em $backups (a rotação só roda depois de um deploy que dá certo); confira o disco"
    fi

    if ! git merge --quiet --ff-only "$sha"; then
        msg "ERRO: git merge --ff-only falhou; nada foi mudado"
        return 1
    fi
    msg "código: $anterior -> $sha"

    local voltar="para voltar: git reset --hard $anterior && docker compose up -d --build (se uma migration nova já rodou, restaure também o $backup)"
    limitado "$limite_compose" docker compose up -d --build --wait --wait-timeout 600
    status=$?
    if [[ $status -ne 0 ]]; then
        falhou "$status" "docker compose up"
        msg "veja: docker compose ps; docker compose logs --tail 100 backend"
        msg "$voltar"
        return 1
    fi
    # O Caddyfile entra por bind mount de um arquivo só, preso ao inode do
    # arquivo antigo: o `git merge` grava um arquivo novo, e um `caddy reload`
    # releria o conteúdo antigo. O `up` não recria o Caddy quando só o
    # Caddyfile muda, então ele é recriado aqui, e o conteúdo é conferido.
    if ! git diff --quiet "$anterior" "$sha" -- Caddyfile; then
        limitado 2m docker compose up -d --no-deps --force-recreate caddy
        status=$?
        if [[ $status -ne 0 ]]; then
            falhou "$status" "a recriação do Caddy (Caddyfile novo)"
            msg "$voltar"
            return 1
        fi
        if ! limitado 1m docker compose exec -T caddy cat /etc/caddy/Caddyfile | cmp -s - Caddyfile; then
            msg "ERRO: o Caddy não vê o Caddyfile novo"
            msg "$voltar"
            return 1
        fi
        msg "Caddy recriado (Caddyfile mudou)"
    fi
    # O PWA (o Caddy não tem healthcheck, então o --wait não o cobre) e a API.
    # As tentativas também cobrem os segundos do Caddy recém-recriado.
    if ! conferir_url "$url/" || ! conferir_url "$url/api/campi/"; then
        msg "$voltar"
        return 1
    fi

    guardar_backups "$backup"
    # Só as imagens sem nome, que cada --build deixa para trás.
    if ! limitado 2m docker image prune -f >/dev/null; then
        msg "AVISO: docker image prune falhou; confira o disco (df -h /; docker system df)"
    fi

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

# A trava fica no descritor 9, como no rodar-comando.sh. O flock -n sai com 1
# quando a trava está presa; outro status é erro do próprio flock.
exec 9>>"$trava"
flock -n 9
status=$?
if [[ $status -ne 0 ]]; then
    if [[ $status -eq 1 ]]; then
        msg "pulado: outro deploy ainda está rodando ($trava)" | tee -p -a "$log"
        logger -t bandejao-deploy -p user.warning -- "deploy de $sha pulado: outro deploy rodando" 2>/dev/null || true
        exit 75
    fi
    msg "ERRO: flock falhou (status $status) em $trava" | tee -p -a "$log"
    logger -t bandejao-deploy -p user.err -- "deploy de $sha: flock falhou" 2>/dev/null || true
    exit 1
fi

corpo 2>&1 | tee -p -a "$log"
status=${PIPESTATUS[0]}
if [[ $status -ne 0 ]]; then
    logger -t bandejao-deploy -p user.err -- "deploy de $sha falhou (ver $log)" 2>/dev/null || true
fi
exit "$status"
