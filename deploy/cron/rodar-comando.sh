#!/bin/sh
# Roda um comando do Django no container do backend, para o cron da VM
# (BD-07, #147). Uso, como azureuser (nunca com sudo, ver o guia):
#
#   sh deploy/cron/rodar-comando.sh <comando> [argumentos]
#
# - Grava o início, a saída do comando e o status em
#   $BANDEJAO_LOGS/<comando>.log (padrão: /var/log/bandejao).
# - O comando roda com `timeout` dentro do container, para o processo do
#   Django morrer junto: $BANDEJAO_TEMPO_LIMITE, padrão 2h, menos que o
#   intervalo de 3 h do ler_cardapio. Status 124 é tempo esgotado.
# - Uma segunda execução do mesmo comando, com a primeira ainda rodando, é
#   pulada e sai com 75 (trava com o flock, do util-linux).
# - Erros e status diferente de 0 também vão para o syslog, com a tag
#   bandejao-cron (journalctl -t bandejao-cron): a VM não manda e-mail, então
#   o cron descarta o stderr.
#
# Status próprios do script: 2 (uso ou nome inválido), 73 (sem escrita no
# log), 75 (pulado). Os outros são do comando.

set -u

TAG=bandejao-cron

# Erro: no stderr, para quem roda à mão, e no syslog, para o cron.
falha() {
    echo "$1" >&2
    logger -t "$TAG" -p user.err -- "$1" 2>/dev/null || true
}

if [ $# -lt 1 ]; then
    falha "uso: sh $0 <comando> [argumentos]"
    exit 2
fi

comando=$1
# Só letras minúsculas, números e "_", como os comandos do Django: o nome vira
# o nome do arquivo de log e da trava.
case $comando in
    '' | [!a-z]* | *[!a-z0-9_]*)
        falha "comando inválido: '$comando'"
        exit 2
        ;;
esac

# A pasta do repositório, onde estão o docker-compose.yml, o .env e o .env.db.
if ! pasta=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd); then
    falha "$comando: pasta do repositório não encontrada"
    exit 1
fi
logs=${BANDEJAO_LOGS:-/var/log/bandejao}
limite=${BANDEJAO_TEMPO_LIMITE:-2h}
log=$logs/$comando.log
trava=$logs/$comando.lock

if ! mkdir -p "$logs" 2>/dev/null; then
    falha "$comando: não foi possível criar $logs"
    exit 1
fi
# A escrita é testada antes: se o log ou a trava forem de outro usuário
# (alguém rodou o script com sudo), o bloco do log nem rodaria e a tarefa
# pararia em silêncio.
# O teste é num subshell: a redireção que falha num builtin especial, como o
# ":", encerraria o próprio script.
for arquivo in "$log" "$trava"; do
    if ! (: >>"$arquivo") 2>/dev/null; then
        falha "$comando: sem permissão de escrita em $arquivo (o script rodou com sudo? ver o guia de deploy)"
        exit 73
    fi
done

if ! cd "$pasta"; then
    falha "$comando: não foi possível entrar em $pasta"
    exit 1
fi

agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

rodar() {
    docker compose exec -T backend \
        timeout --kill-after=60 "$limite" python manage.py "$@"
}

status=1
{
    echo "[$(agora)] início: $*"
    if command -v flock >/dev/null 2>&1; then
        # A trava fica no descritor 9 deste shell, separada do comando: o
        # status do comando, mesmo um 75, nunca é confundido com "pulado".
        exec 9>>"$trava"
        if flock -n 9; then
            rodar "$@" 9>&-
            status=$?
        else
            status=75
            echo "[$(agora)] pulado: a execução anterior ainda está rodando"
        fi
    else
        echo "[$(agora)] aviso: sem flock, rodando sem a trava contra execução dupla"
        rodar "$@"
        status=$?
    fi
    if [ "$status" -eq 124 ]; then
        echo "[$(agora)] tempo esgotado ($limite)"
    fi
    echo "[$(agora)] fim: status $status"
} >>"$log" 2>&1

case $status in
    0) ;;
    75)
        logger -t "$TAG" -p user.warning -- \
            "$comando: pulado, a execução anterior ainda está rodando" \
            2>/dev/null || true
        ;;
    *) falha "$comando: terminou com status $status (ver $log)" ;;
esac

exit "$status"
