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
#   intervalo de 3 h do ler_cardapio. Status 124 é tempo esgotado; 137, o
#   processo morto com KILL (não saiu com o TERM, ou faltou memória).
# - O cliente do docker, no host, tem o próprio limite, um pouco maior
#   ($BANDEJAO_TEMPO_LIMITE_CLIENTE, padrão 130m), para um `docker compose
#   exec` travado não segurar a trava para sempre. Se trocar um limite,
#   mantenha o do cliente maior que o do container.
# - Uma segunda execução do mesmo comando, com a primeira ainda rodando, é
#   pulada e sai com 75 (trava com o flock, do util-linux).
# - Erros e status diferente de 0 também vão para o syslog, com a tag
#   bandejao-cron (journalctl -t bandejao-cron): a VM não manda e-mail, então
#   o cron descarta o stderr.
#
# Status próprios do script que saem antes do log, e por isso só aparecem no
# syslog: 1 (pasta do repositório, mkdir ou cd), 2 (uso ou nome inválido) e
# 73 (sem escrita no log ou na trava). Depois do log: 75 (pulado); os outros
# vêm do comando ou do timeout.

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
limite_cliente=${BANDEJAO_TEMPO_LIMITE_CLIENTE:-130m}
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

# A entrada é vazia (</dev/null, o fim do arquivo na hora): o comando do Django
# não lê nada, e num terminal (rodando à mão, por SSH) o `docker compose
# exec -T` herdaria o terminal. Como o `timeout` o põe em segundo plano, o
# kernel o pararia com SIGTTIN (estado `T`), e a trava ficaria presa até o
# limite do cliente. Pelo cron não há terminal, por isso lá nunca aconteceu.
# Não troque por `timeout --foreground`: o limite do cliente ainda encerra o
# `docker`, mas um filho dele pode continuar vivo e segurando a trava.
rodar() {
    timeout --kill-after=60 "$limite_cliente" \
        docker compose exec -T backend \
        timeout --kill-after=60 "$limite" python manage.py "$@" </dev/null
}

status=1
pulado=0
{
    echo "[$(agora)] início: $*"
    if command -v flock >/dev/null 2>&1; then
        # A trava fica no descritor 9, separada do comando: o status do
        # comando, mesmo um 75, nunca é confundido com "pulado". O docker
        # herda o descritor, então a trava continua presa se este shell
        # morrer no meio da execução.
        exec 9>>"$trava"
        if flock -n 9; then
            rodar "$@"
            status=$?
        else
            status=75
            pulado=1
            echo "[$(agora)] pulado: a execução anterior ainda está rodando"
        fi
    else
        echo "[$(agora)] aviso: sem flock, rodando sem a trava contra execução dupla"
        rodar "$@"
        status=$?
    fi
    case $status in
        124) echo "[$(agora)] tempo esgotado ($limite no container, $limite_cliente no cliente)" ;;
        137) echo "[$(agora)] encerrado à força (KILL): não saiu depois do tempo esgotado, ou faltou memória" ;;
    esac
    echo "[$(agora)] fim: status $status"
} >>"$log" 2>&1

# O pulo vem da variável, e não do status: um 75 do próprio comando é erro.
if [ "$pulado" -eq 1 ]; then
    logger -t "$TAG" -p user.warning -- \
        "$comando: pulado, a execução anterior ainda está rodando" \
        2>/dev/null || true
elif [ "$status" -ne 0 ]; then
    falha "$comando: terminou com status $status (ver $log)"
fi

exit "$status"
