#!/bin/sh
# Teste de restauração do backup (BD-15, #183). Uso, como azureuser:
#
#   sh deploy/backup/testar-restauracao.sh [arquivo.sql.gz]
#
# Sem argumento, usa a cópia mais recente de $BANDEJAO_BACKUPS (padrão:
# /var/backups/bandejao). Sobe um MySQL 8.4 temporário, SEM rede e com senha
# aleatória, restaura a cópia nele e compara com o banco de produção: o
# número de tabelas tem que ser o mesmo e o `django_migrations` não pode
# estar vazio, e, se a produção tem contas, o `cadastro_usuario` não pode estar
# vazio nem ter menos da metade delas: um banco recém-criado gera um dump
# completo e sem contas. Com 0 contas dos dois lados, passa com um AVISO: a
# restauração prova a estrutura, mas não os dados. (Uma tabela qualquer com linhas não basta: a tabela de cache do
# limite de taxa enche com uma tentativa de login.) A tabela de cache
# (`cache_bandejao`) fica fora do backup e da contagem de tabelas. Mostra
# também as linhas de cada tabela, para conferir a olho. As senhas vão ao
# MySQL pelo ambiente (`MYSQL_PWD`), nunca como argumento.
# O container temporário some no fim (com `--rm`, o volume dele também). O
# banco de produção só é lido, nunca alterado.
#
# Status: 0 (restauração conferida), 1 (falha), 2 (uso).

set -u

backups=${BANDEJAO_BACKUPS:-/var/backups/bandejao}
banco=${BANDEJAO_BANCO:-bandejao}
nome=bandejao-teste-restauracao
espera=${BANDEJAO_ESPERA_TESTE:-90}   # tentativas de espera pelo MySQL
pausa=${BANDEJAO_PAUSA_TESTE:-2}      # segundos entre as tentativas

erro=''

fim() {
    echo "FALHA: $1" >&2
    if [ -n "$erro" ] && [ -s "$erro" ]; then
        echo "Último erro:" >&2
        grep -v 'Using a password' "$erro" | tail -n 3 >&2
    fi
    exit 1
}

case $banco in
    '' | *[!A-Za-z0-9_]*)
        echo "BANDEJAO_BANCO inválido: '$banco'" >&2
        exit 2
        ;;
esac
for valor in "$espera" "$pausa"; do
    case $valor in
        '' | *[!0-9]*)
            echo "BANDEJAO_ESPERA_TESTE e BANDEJAO_PAUSA_TESTE precisam ser números: '$valor'" >&2
            exit 2
            ;;
    esac
done

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

# `-v` remove também o volume anônimo do MySQL: a cópia inteira da produção
# não pode ficar no disco.
limpar() {
    docker rm -f -v "$nome" >/dev/null 2>&1 || true
    [ -z "$erro" ] || rm -f "$erro"
}
# O `sh` (dash) não roda o trap de EXIT num Ctrl-C ou kill: o sinal vira um
# exit, que dispara o limpar.
trap 'echo "Interrompido: removendo o container temporário." >&2; exit 130' INT TERM HUP
trap limpar EXIT
# Sobra de uma execução anterior interrompida.
docker rm -f -v "$nome" >/dev/null 2>&1 || true
erro=$(mktemp "${TMPDIR:-/tmp}/bandejao-restauracao.XXXXXX") || fim "não foi possível criar o arquivo temporário"

echo "Restaurando $(basename -- "$arquivo") num MySQL temporário..."
# A senha vai pelo ambiente do `docker run` (-e sem valor), e não como
# argumento: não aparece no `ps` do host.
MYSQL_ROOT_PASSWORD="$senha" docker run -d --rm --name "$nome" --network none \
    -e MYSQL_ROOT_PASSWORD -e MYSQL_DATABASE="$banco" \
    mysql:8.4 >/dev/null || fim "não foi possível subir o container temporário"

# O MySQL sobe um servidor provisório para o init e reinicia: só vale depois
# da mensagem final do init.
pronto=0
i=0
while [ "$i" -lt "$espera" ]; do
    if docker logs "$nome" 2>&1 | grep -q 'MySQL init process done'; then
        if docker exec "$nome" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqladmin ping -uroot --silent' >/dev/null 2>&1; then
            pronto=1
            break
        fi
    fi
    i=$((i + 1))
    sleep "$pausa"
done
[ "$pronto" -eq 1 ] || fim "o MySQL temporário não ficou pronto a tempo"

gzip -dc "$arquivo" | docker exec -i "$nome" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot "$1"' sh "$banco" 2>"$erro" \
    || fim "erro ao restaurar o dump"

# O stderr das consultas fica em $erro e sai no `fim`: senha errada, container
# morto e erro de SQL não podem parecer "tabela ausente". O `</dev/null` evita
# que o `docker compose exec -T` espere o teclado quando o script roda à mão.
consulta_temp() {
    docker exec "$nome" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot -N -B "$1" -e "$2"' sh "$banco" "$1" </dev/null 2>"$erro"
}
consulta_prod() {
    docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot -N -B "$1" -e "$2"' sh "$banco" "$1" </dev/null 2>"$erro"
}

contar="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name <> 'cache_bandejao'"
tabelas_temp=$(consulta_temp "$contar") || fim "não consegui contar as tabelas restauradas"
tabelas_prod=$(consulta_prod "$contar") || fim "não consegui contar as tabelas de produção"
migracoes=$(consulta_temp 'SELECT COUNT(*) FROM django_migrations') || fim "não consegui contar django_migrations no backup (a tabela existe?)"

echo "Tabelas: restauradas=$tabelas_temp, produção=$tabelas_prod; migrações restauradas=$migracoes"
[ "$tabelas_temp" = "$tabelas_prod" ] || fim "o número de tabelas difere do banco de produção"
[ "${migracoes:-0}" -gt 0 ] || fim "o django_migrations restaurado está vazio"

# Contas: o dump sem `cadastro_usuario` povoado é um banco recriado, mesmo que
# outras tabelas (a de cache, por exemplo) tenham linhas.
usuarios_temp=$(consulta_temp 'SELECT COUNT(*) FROM cadastro_usuario') || fim "não consegui contar cadastro_usuario no backup"
usuarios_prod=$(consulta_prod 'SELECT COUNT(*) FROM cadastro_usuario') || fim "não consegui contar cadastro_usuario na produção"
echo "Contas: restauradas=$usuarios_temp, produção=$usuarios_prod"
if [ "${usuarios_prod:-0}" -gt 0 ]; then
    [ "${usuarios_temp:-0}" -gt 0 ] || fim "cadastro_usuario restaurado está vazio, e a produção tem $usuarios_prod contas: o backup não tem dados"
    [ $((usuarios_temp * 2)) -ge "$usuarios_prod" ] || fim "cadastro_usuario restaurado ($usuarios_temp) tem menos da metade das contas da produção ($usuarios_prod)"
else
    echo "AVISO: a produção também tem 0 contas; a restauração prova a estrutura, mas não confere os dados."
fi

# Contagem exata (COUNT(*)): a estimativa de linhas do information_schema é só uma
# aproximação e aparece 0 logo depois de uma restauração.
lista=$(consulta_temp "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() ORDER BY table_name") \
    || fim "não consegui listar as tabelas restauradas"
[ -n "$lista" ] || fim "a lista de tabelas restauradas veio vazia"
echo "Linhas por tabela (restaurado):"
for tabela in $lista; do
    linhas=$(consulta_temp "SELECT COUNT(*) FROM \`$tabela\`") || fim "não consegui contar as linhas de $tabela"
    printf '  %s\t%s\n' "$tabela" "$linhas"
done

echo "OK: a restauração de $(basename -- "$arquivo") foi conferida."
exit 0
