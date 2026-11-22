#!/bin/sh
# Backup diário do banco de produção (BD-15, #183). Uso, como azureuser
# (nunca com sudo, ver o guia):
#
#   sh deploy/backup/backup-banco.sh
#
# - Faz um mysqldump consistente (--single-transaction) do banco, dentro do
#   container `db`, comprime e guarda em $BANDEJAO_BACKUPS (padrão:
#   /var/backups/bandejao), com permissão 600 numa pasta 700: o mesmo acesso
#   restrito do banco (ADR 0008). A senha do root fica só dentro do container
#   (`$MYSQL_ROOT_PASSWORD` do .env.db); não passa por este script.
# - O arquivo só ganha o nome final depois de conferido: o gzip íntegro e a
#   última linha do dump (`-- Dump completed`). Um dump pela metade nunca vira
#   backup.
# - Guarda 7 dias (Anexo A, $BANDEJAO_RETENCAO_DIAS): o que tem mais que isso
#   é apagado, para que os dados de uma conta excluída também saiam dos
#   backups (RNF07.4). A rotação roda antes do dump e mesmo que o dump
#   falhe: o prazo vale mais que a quantidade de cópias.
# - Erros vão para o syslog, com a tag bandejao-backup (journalctl -t
#   bandejao-backup): a VM não manda e-mail.
#
# Status: 0 (ok), 1 (falha), 2 (uso ou configuração inválida), 75 (já tem um
# backup rodando).

set -u

TAG=bandejao-backup

falha() {
    echo "$1" >&2
    logger -t "$TAG" -p user.err -- "$1" 2>/dev/null || true
}

agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

backups=${BANDEJAO_BACKUPS:-/var/backups/bandejao}
retencao=${BANDEJAO_RETENCAO_DIAS:-7}
banco=${BANDEJAO_BANCO:-bandejao}
limite=${BANDEJAO_TEMPO_LIMITE:-30m}

case $retencao in
    '' | *[!0-9]* | 0)
        falha "BANDEJAO_RETENCAO_DIAS inválido: '$retencao' (use um número de dias, 1 ou mais)"
        exit 2
        ;;
esac
case $banco in
    '' | *[!A-Za-z0-9_]*)
        falha "BANDEJAO_BANCO inválido: '$banco'"
        exit 2
        ;;
esac

# Arquivos novos só para o dono (600) e pastas novas 700.
umask 077

if ! pasta=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd); then
    falha "backup: pasta do repositório não encontrada"
    exit 1
fi

if [ ! -d "$backups" ]; then
    falha "backup: $backups não existe (criar com: sudo install -d -m 700 -o azureuser -g azureuser $backups)"
    exit 1
fi
if [ ! -w "$backups" ]; then
    falha "backup: sem permissão de escrita em $backups (o script rodou com sudo? ver o guia)"
    exit 1
fi
chmod 700 "$backups" 2>/dev/null || true

# Uma execução por vez.
if command -v flock >/dev/null 2>&1; then
    exec 9>>"$backups/.trava"
    if ! flock -n 9; then
        echo "[$(agora)] pulado: o backup anterior ainda está rodando"
        logger -t "$TAG" -p user.warning -- "backup pulado: o anterior ainda está rodando" 2>/dev/null || true
        exit 75
    fi
fi

echo "[$(agora)] início do backup de $banco"

# --- rotação: o prazo vale mesmo que o dump de hoje falhe -------------------
# Minutos, e não dias do find: com -mtime +6 uma cópia de 6 dias e 23 h ainda
# ficaria, e a pasta teria 8 cópias. A folga de 2 h cobre a variação de
# horário do cron.
minutos=$((retencao * 24 * 60 - 120))
if ! find "$backups" -maxdepth 1 -type f -name 'bandejao-*.sql.gz' -mmin +"$minutos" -delete; then
    falha "backup: erro ao apagar as cópias com mais de $retencao dias em $backups"
    exit 1
fi
# Sobra de um backup interrompido (tmp com mais de 1 dia).
find "$backups" -maxdepth 1 -type f -name '.bandejao-*.tmp*' -mmin +1440 -delete 2>/dev/null || true

# --- dump ------------------------------------------------------------------
ts=$(date -u '+%Y%m%dT%H%M%SZ')
final=$backups/bandejao-$ts.sql.gz
bruto=$backups/.bandejao-$ts.tmp
gz=$backups/.bandejao-$ts.tmp.gz
erros=$backups/.bandejao-$ts.tmp.err

limpar() { rm -f "$bruto" "$gz" "$erros"; }
trap limpar EXIT

if ! cd "$pasta"; then
    falha "backup: não foi possível entrar em $pasta"
    exit 1
fi

# A senha vem do ambiente do container; o nome do banco entra como argumento.
# A entrada é fechada (</dev/null): num terminal, o `docker compose exec -T`
# dentro do `timeout` ficava esperando o teclado e o backup travava em
# silêncio. No cron não há terminal, mas o comportamento tem que ser o mesmo.
timeout --kill-after=60 "$limite" \
    docker compose exec -T db sh -c \
    'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --default-character-set=utf8mb4 --no-tablespaces "$1"' \
    sh "$banco" </dev/null >"$bruto" 2>"$erros"
status=$?
if [ "$status" -ne 0 ]; then
    # Só as primeiras linhas do erro do mysqldump, sem o aviso da senha na
    # linha de comando: o erro não traz dado do banco.
    detalhe=$(grep -v 'Using a password' "$erros" 2>/dev/null | head -n 3 | tr '\n' ' ')
    falha "backup: mysqldump terminou com status $status ${detalhe:+($detalhe)}"
    exit 1
fi

if [ ! -s "$bruto" ] || ! tail -n 1 "$bruto" | grep -q '^-- Dump completed'; then
    falha "backup: o dump veio incompleto (sem a linha '-- Dump completed'); nada foi guardado"
    exit 1
fi

if ! gzip -c "$bruto" >"$gz" || ! gzip -t "$gz"; then
    falha "backup: erro ao comprimir o dump; nada foi guardado"
    exit 1
fi

chmod 600 "$gz"
if ! mv "$gz" "$final"; then
    falha "backup: não foi possível gravar $final"
    exit 1
fi

copias=$(find "$backups" -maxdepth 1 -type f -name 'bandejao-*.sql.gz' | wc -l | tr -d ' ')
tamanho=$(wc -c <"$final" | tr -d ' ')
echo "[$(agora)] ok: $(basename -- "$final") ($tamanho bytes); $copias cópia(s) guardada(s), prazo de $retencao dias"
exit 0
