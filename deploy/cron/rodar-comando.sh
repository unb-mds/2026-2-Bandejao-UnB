#!/bin/sh
# Roda um comando do Django no container do backend, para o cron da VM
# (BD-07, #147). Uso:
#
#   sh deploy/cron/rodar-comando.sh <comando> [argumentos]
#
# Grava o início, a saída do comando e o status em
# $BANDEJAO_LOGS/<comando>.log (padrão: /var/log/bandejao) e sai com o status
# do comando. Uma segunda execução do mesmo comando, com a primeira ainda
# rodando, é pulada e sai com 75; sem o flock (util-linux), roda sem a trava.

set -u

if [ $# -lt 1 ]; then
    echo "uso: sh $0 <comando> [argumentos]" >&2
    exit 2
fi

comando=$1
# Só letras minúsculas, números e "_", como os comandos do Django: o nome vira
# o nome do arquivo de log e da trava.
case $comando in
    '' | [!a-z]* | *[!a-z0-9_]*)
        echo "comando inválido: '$comando'" >&2
        exit 2
        ;;
esac

# A pasta do repositório, onde estão o docker-compose.yml, o .env e o .env.db.
pasta=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd) || exit 1
logs=${BANDEJAO_LOGS:-/var/log/bandejao}
mkdir -p "$logs" || exit 1
log=$logs/$comando.log
trava=$logs/$comando.lock

agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

cd "$pasta" || exit 1

{
    echo "[$(agora)] início: $*"
    if command -v flock >/dev/null 2>&1; then
        flock -n -E 75 "$trava" docker compose exec -T backend python manage.py "$@"
    else
        docker compose exec -T backend python manage.py "$@"
    fi
    status=$?
    if [ "$status" -eq 75 ]; then
        echo "[$(agora)] pulado: a execução anterior ainda está rodando"
    fi
    echo "[$(agora)] fim: status $status"
} >>"$log" 2>&1

exit "$status"
