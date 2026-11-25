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
#   (`$MYSQL_ROOT_PASSWORD` do .env.db) e vai ao mysqldump pelo ambiente
#   (`MYSQL_PWD`), nunca como argumento: não aparece no `ps`.
# - O arquivo só ganha o nome final depois de conferido: o gzip íntegro e a
#   última linha do dump (`-- Dump completed`). Um dump pela metade nunca vira
#   backup.
# - Guarda 7 dias (Anexo A, $BANDEJAO_RETENCAO_DIAS): o que tem mais que isso
#   é apagado, para que os dados de uma conta excluída também saiam dos
#   backups (RNF07.4). A rotação roda antes do dump e mesmo que o dump
#   falhe: o prazo vale mais que a quantidade de cópias. Por isso, quando uma
#   falha deixa a pasta sem cópia, ou com a mais nova com mais de 26 h, o
#   script avisa no syslog com prioridade user.crit.
#   A rotação roda logo depois de a pasta ser conferida, **antes** do teste de
#   escrita do log e da trava: se o log nasceu como root (alguém rodou com
#   sudo), o script sai com 73, mas as cópias velhas já saíram, e o `crit` vale
#   também para essas saídas.
# - O script grava o próprio log em $BANDEJAO_LOGS/backup-banco.log (padrão:
#   /var/log/bandejao) e testa a escrita antes, como o rodar-comando.sh do
#   BD-07: a linha do cron não tem redireção, para o cron não parar em
#   silêncio se o log não for gravável. Erros e o resumo de cada execução
#   também vão para o syslog, com a tag bandejao-backup
#   (journalctl -t bandejao-backup): a VM não manda e-mail.
# - O dump roda com `timeout` dentro do container, para o mysqldump morrer
#   junto (o do cliente, no host, é um pouco maior). Status 124 é tempo
#   esgotado; 137, processo morto com KILL.
# - A tabela de cache do Django (`cache_bandejao`, limite de taxa, com chaves
#   que podem ter IP) fica fora do dump: é efêmera e não precisa de 7 dias de
#   backup. Depois de restaurar num banco vazio, rode `createcachetable`.
#
# Status: 0 (ok), 1 (falha), 2 (uso ou configuração inválida), 73 (sem escrita
# no log ou na trava), 75 (já tem um backup rodando), 130 (interrompido).

set -u

TAG=bandejao-backup

# O descritor 3 guarda o stderr original: depois que o script passa a gravar
# no log, é por ele que quem roda à mão (e o cron) ainda vê os erros.
exec 3>&2
logando=0

agora() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

# Erro: no log (se já estiver aberto), no terminal/stderr e no syslog.
falha() {
    if [ "$logando" -eq 1 ]; then echo "[$(agora)] $1"; fi
    echo "$1" >&3
    logger -t "$TAG" -p user.err -- "$1" 2>/dev/null || true
}

aviso() {
    if [ "$logando" -eq 1 ]; then echo "[$(agora)] aviso: $1"; fi
    logger -t "$TAG" -p "${2:-user.warning}" -- "$1" 2>/dev/null || true
}

backups=${BANDEJAO_BACKUPS:-/var/backups/bandejao}
logs=${BANDEJAO_LOGS:-/var/log/bandejao}
retencao=${BANDEJAO_RETENCAO_DIAS:-7}
banco=${BANDEJAO_BANCO:-bandejao}
limite=${BANDEJAO_TEMPO_LIMITE:-30m}
limite_cliente=${BANDEJAO_TEMPO_LIMITE_CLIENTE:-35m}
log=$logs/backup-banco.log

case $retencao in
    '' | *[!0-9]* | 0* | ?????*)
        # Zero à esquerda fica de fora: `00` dava minutos negativos e a
        # rotação apagava todas as cópias, `08` quebrava a conta do `sh` e
        # `010` era lido como octal. Mais de 4 dígitos estoura a conta.
        falha "BANDEJAO_RETENCAO_DIAS inválido: '$retencao' (use um número de dias de 1 a 9999, sem zero à esquerda)"
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

# Sem cópia, ou com a mais nova velha demais, é o único caso em que o prazo
# da rotação deixa a pasta sem backup útil: avisa alto.
conferir_pasta() {
    total=$(find "$backups" -maxdepth 1 -type f -name 'bandejao-*.sql.gz' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$total" -eq 0 ]; then
        aviso "SEM NENHUMA CÓPIA em $backups: o backup não foi feito (ver o log) ou a rotação apagou o resto" user.crit
    elif [ -z "$(find "$backups" -maxdepth 1 -type f -name 'bandejao-*.sql.gz' -mmin -1560 2>/dev/null | head -n 1)" ]; then
        aviso "a cópia mais nova de $backups tem mais de 26 h: o backup de hoje não foi feito (falhou ou foi pulado)" user.crit
    fi
}

# Saída com status próprio (73, 75, 1...) conferindo antes a pasta: o aviso
# `crit` não pode depender de o script ter chegado até o dump.
sair_com() {
    conferir_pasta
    exit "$1"
}

abortar() {
    falha "$1"
    sair_com 1
}

if ! pasta=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd); then
    falha "backup: pasta do repositório não encontrada"
    exit 1
fi

if [ ! -d "$backups" ]; then
    falha "backup: $backups não existe (criar com: sudo install -d -m 700 -o azureuser -g azureuser $backups)"
    sair_com 1
fi
if [ ! -w "$backups" ]; then
    falha "backup: sem permissão de escrita em $backups (o script rodou com sudo? ver o guia)"
    sair_com 1
fi
chmod 700 "$backups" 2>/dev/null || true

# --- rotação: o prazo vale mesmo que o dump de hoje falhe, e mesmo que o log
# ou a trava não possam ser gravados (por isso vem antes dos testes abaixo) ---
# Minutos, e não dias do find: com -mtime +6 uma cópia de 6 dias e 23 h ainda
# ficaria, e a pasta teria 8 cópias. A folga de 2 h cobre a variação de
# horário do cron.
minutos=$((retencao * 24 * 60 - 120))
if ! find "$backups" -maxdepth 1 -type f -name 'bandejao-*.sql.gz' -mmin +"$minutos" -delete; then
    abortar "backup: erro ao apagar as cópias com mais de $retencao dias em $backups"
fi
# Sobra de um backup interrompido (tmp com mais de 1 dia).
find "$backups" -maxdepth 1 -type f -name '.bandejao-*.tmp*' -mmin +1440 -delete 2>/dev/null || true

if ! mkdir -p "$logs" 2>/dev/null; then
    falha "backup: não foi possível criar $logs"
    sair_com 1
fi
# A escrita do log e da trava é testada antes: se forem de outro usuário
# (alguém rodou o script com sudo), o backup pararia em silêncio. O teste é
# num subshell, porque uma redireção que falha num builtin especial como o
# ":" encerraria o próprio script.
trava=$backups/.trava
for arquivo in "$log" "$trava"; do
    if ! (: >>"$arquivo") 2>/dev/null; then
        falha "backup: sem permissão de escrita em $arquivo (o script rodou com sudo? ver o guia)"
        sair_com 73
    fi
done

# A partir daqui, tudo o que o script escreve vai para o log.
exec >>"$log" 2>&1
logando=1

# Interrupção (Ctrl-C, kill): o `sh` (dash) não roda o trap de EXIT sozinho,
# então o sinal vira um exit, que dispara o trap abaixo. O aviso deixa rastro
# no log e no syslog (um TERM do systemd num reboot, por exemplo).
trap 'falha "backup: interrompido por sinal"; exit 130' INT TERM HUP

# Uma execução por vez. O `flock -n` sai com 1 quando a trava está ocupada;
# outro status é erro do próprio flock e não pode virar "pulado".
if command -v flock >/dev/null 2>&1; then
    exec 9>>"$trava"
    flock -n 9
    trava_status=$?
    if [ "$trava_status" -eq 1 ]; then
        echo "[$(agora)] pulado: o backup anterior ainda está rodando"
        logger -t "$TAG" -p user.warning -- "backup pulado: o anterior ainda está rodando" 2>/dev/null || true
        sair_com 75
    elif [ "$trava_status" -ne 0 ]; then
        falha "backup: erro ao pegar a trava (flock saiu com status $trava_status)"
        sair_com 1
    fi
else
    aviso "sem flock: rodando sem a trava contra execução dupla"
fi

echo "[$(agora)] início do backup de $banco"

# --- dump ------------------------------------------------------------------
ts=$(date -u '+%Y%m%dT%H%M%SZ')
final=$backups/bandejao-$ts.sql.gz
bruto=$backups/.bandejao-$ts.tmp
gz=$backups/.bandejao-$ts.tmp.gz
erros=$backups/.bandejao-$ts.tmp.err

limpar() { rm -f "$bruto" "$gz" "$erros"; }
trap limpar EXIT

if ! cd "$pasta"; then
    abortar "backup: não foi possível entrar em $pasta"
fi

# A cópia anterior, para comparar o tamanho depois.
anterior=$(ls -1t "$backups"/bandejao-*.sql.gz 2>/dev/null | head -n 1)

# A senha vem do ambiente do container (MYSQL_PWD, e não -p, para não aparecer
# na lista de processos); o nome do banco entra como argumento. O `timeout`
# de dentro do container mata o mysqldump; o do cliente, no host, é um pouco
# maior e só evita que um `docker compose exec` travado segure a trava para
# sempre. A entrada é fechada (</dev/null): num terminal, o `docker compose
# exec -T` ficava esperando o teclado e o backup travava em silêncio.
# O `--foreground` mantém o `timeout` no grupo do terminal: sem ele, um Ctrl-C
# não chegaria ao dump e o script só reagiria quando ele terminasse.
# A tabela de cache do limite de taxa fica fora (ver o cabeçalho).
timeout --foreground --kill-after=60 "$limite_cliente" \
    docker compose exec -T db \
    timeout --kill-after=60 "$limite" sh -c \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --routines --triggers --default-character-set=utf8mb4 --no-tablespaces --ignore-table="$1.cache_bandejao" "$1"' \
    sh "$banco" </dev/null >"$bruto" 2>"$erros"
status=$?
if [ "$status" -ne 0 ]; then
    # Só as primeiras linhas do erro do mysqldump: o erro não traz dado do
    # banco. (O grep do aviso de senha é só proteção: com MYSQL_PWD ele não
    # aparece.)
    detalhe=$(grep -v 'Using a password' "$erros" 2>/dev/null | head -n 3 | tr '\n' ' ')
    case $status in
        124) motivo="tempo esgotado ($limite no container, $limite_cliente no cliente)" ;;
        137) motivo="encerrado à força (KILL): não saiu depois do tempo esgotado, ou faltou memória" ;;
        127) motivo="comando não encontrado (o container db tem o 'timeout'?)" ;;
        *) motivo="terminou com status $status" ;;
    esac
    abortar "backup: mysqldump $motivo ${detalhe:+($detalhe)}"
fi

if [ ! -s "$bruto" ] || ! tail -n 1 "$bruto" | grep -q '^-- Dump completed'; then
    abortar "backup: o dump veio incompleto (sem a linha '-- Dump completed'); nada foi guardado"
fi

if ! gzip -c "$bruto" >"$gz" || ! gzip -t "$gz"; then
    abortar "backup: erro ao comprimir o dump; nada foi guardado"
fi

chmod 600 "$gz"
if ! mv "$gz" "$final"; then
    abortar "backup: não foi possível gravar $final"
fi

tamanho=$(wc -c <"$final" | tr -d ' ')
# Banco vazio (um `down -v` seguido de migrate) gera um dump completo e
# pequeno: o tamanho que despenca é o sinal.
if [ -n "$anterior" ] && [ -f "$anterior" ]; then
    antes=$(wc -c <"$anterior" | tr -d ' ')
    if [ "$antes" -gt 0 ] && [ $((tamanho * 2)) -lt "$antes" ]; then
        aviso "$(basename -- "$final") tem $tamanho bytes, menos da metade da cópia anterior ($antes): conferir se o banco perdeu dados"
    fi
fi

copias=$(find "$backups" -maxdepth 1 -type f -name 'bandejao-*.sql.gz' | wc -l | tr -d ' ')
resumo="ok: $(basename -- "$final") ($tamanho bytes); $copias cópia(s) guardada(s), prazo de $retencao dias"
echo "[$(agora)] $resumo"
logger -t "$TAG" -p user.info -- "$resumo" 2>/dev/null || true
exit 0
