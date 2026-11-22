#!/bin/sh
# Teste de restauração do backup (BD-15, #183). Uso, como azureuser:
#
#   sh deploy/backup/testar-restauracao.sh [arquivo.sql.gz]
#
# Sem argumento, usa a cópia mais recente de $BANDEJAO_BACKUPS (padrão:
# /var/backups/bandejao). Sobe um MySQL 8.4 temporário, SEM rede e com senha
# aleatória, restaura a cópia nele e compara com o banco de produção: o
# número de tabelas tem que ser o mesmo e o `django_migrations` não pode
# estar vazio. Mostra também as linhas de cada tabela, para conferir a olho.
# O container temporário some no fim (com `--rm`, o volume dele também). O
# banco de produção só é lido, nunca alterado.
#
# Status: 0 (restauração conferida), 1 (falha), 2 (uso).

set -u

backups=${BANDEJAO_BACKUPS:-/var/backups/bandejao}
banco=${BANDEJAO_BANCO:-bandejao}
nome=bandejao-teste-restauracao
espera=${BANDEJAO_ESPERA_TESTE:-90}

fim() {
    echo "FALHA: $1" >&2
    exit 1
}

case $banco in
    '' | *[!A-Za-z0-9_]*)
        echo "BANDEJAO_BANCO inválido: '$banco'" >&2
        exit 2
        ;;
esac

if [ $# -ge 1 ]; then
    arquivo=$1
else
    arquivo=$(ls -1t "$backups"/bandejao-*.sql.gz 2>/dev/null | head -n 1)
fi
[ -n "${arquivo:-}" ] && [ -f "$arquivo" ] || fim "nenhum backup encontrado em $backups"
gzip -t "$arquivo" || fim "o arquivo $arquivo não é um gzip íntegro"

if ! pasta=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd); then
    fim "pasta do repositório não encontrada"
fi
cd "$pasta" || fim "não foi possível entrar em $pasta"

senha=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')

limpar() { docker rm -f "$nome" >/dev/null 2>&1 || true; }
trap limpar EXIT
limpar

echo "Restaurando $(basename -- "$arquivo") num MySQL temporário..."
docker run -d --rm --name "$nome" --network none \
    -e MYSQL_ROOT_PASSWORD="$senha" -e MYSQL_DATABASE="$banco" \
    mysql:8.4 >/dev/null || fim "não foi possível subir o container temporário"

# O MySQL sobe um servidor provisório para o init e reinicia: só vale depois
# da mensagem final do init.
pronto=0
i=0
while [ "$i" -lt "$espera" ]; do
    if docker logs "$nome" 2>&1 | grep -q 'MySQL init process done'; then
        if docker exec "$nome" mysqladmin ping -uroot -p"$senha" --silent >/dev/null 2>&1; then
            pronto=1
            break
        fi
    fi
    i=$((i + 1))
    sleep 2
done
[ "$pronto" -eq 1 ] || fim "o MySQL temporário não ficou pronto a tempo"

gzip -dc "$arquivo" | docker exec -i "$nome" mysql -uroot -p"$senha" "$banco" \
    || fim "erro ao restaurar o dump"

consulta_temp() {
    docker exec "$nome" mysql -uroot -p"$senha" -N -B "$banco" -e "$1" 2>/dev/null
}
consulta_prod() {
    docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B "$1" -e "$2"' sh "$banco" "$1" 2>/dev/null
}

contar='SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()'
tabelas_temp=$(consulta_temp "$contar") || fim "não consegui contar as tabelas restauradas"
tabelas_prod=$(consulta_prod "$contar") || fim "não consegui contar as tabelas de produção"
migracoes=$(consulta_temp 'SELECT COUNT(*) FROM django_migrations') || fim "django_migrations ausente no backup"

echo "Tabelas: restauradas=$tabelas_temp, produção=$tabelas_prod; migrações restauradas=$migracoes"
[ "$tabelas_temp" = "$tabelas_prod" ] || fim "o número de tabelas difere do banco de produção"
[ "${migracoes:-0}" -gt 0 ] || fim "o django_migrations restaurado está vazio"

echo "Linhas por tabela (restaurado):"
consulta_temp "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema=DATABASE() ORDER BY table_name" | sed 's/^/  /'

echo "OK: a restauração de $(basename -- "$arquivo") foi conferida."
exit 0
