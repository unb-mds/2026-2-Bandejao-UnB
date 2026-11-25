#!/bin/sh
# Usuários do MySQL de produção (BD-05, ADR 0004, 0008 e 0012).
#
# Roda sozinho na PRIMEIRA subida do container db, com o volume vazio, logo
# depois de a imagem criar o banco (MYSQL_DATABASE) e o usuário da aplicação
# (MYSQL_USER). Para aplicar de novo num banco que já existe:
#
#   docker compose up -d --force-recreate --wait db
#   docker compose exec db sh /docker-entrypoint-initdb.d/10-usuarios.sh
#
# Pode rodar quantas vezes for preciso: cada comando confere o que já existe.
#
# 1. Usuário da aplicação: a imagem dá a ele ALL PRIVILEGES no banco. O script
#    deixa só o que o Django usa: ler e gravar dados e, nas migrations que o
#    entrypoint.sh aplica a cada subida, criar e alterar tabelas e índices.
#    Nada fora do banco da aplicação (nenhum GRANT em *.*).
# 2. Papel equipe_moderacao: ler e alterar dados para a moderação (ADR 0004),
#    sem mudar a estrutura das tabelas, que é das migrations. O DELETE é para
#    as avaliações; a exclusão de conta é só pelo RemoverContaCommand, nunca
#    por DELETE direto (o cascade e o SET NULL são do ORM, não do banco).
# 3. Usuário da equipe (DB_EQUIPE_USER), com esse papel. A ADR 0012 pede um
#    usuário por membro: os demais são criados à mão, como no guia de deploy
#    (docs/deploy/deploy-producao.md).
#
# As senhas vêm do .env.db (o container db não recebe o .env do backend), e o
# usuário e o banco da aplicação vêm do .env, pelo Compose. Nada vem do Git.
#
# A imagem do MySQL roda este arquivo com "source" (ele não é executável) e
# com "set -e". Por isso tudo fica em funções com prefixo, e o script não usa
# "exit": o exit encerraria o entrypoint da imagem, mesmo com status 0.
#
# Se um comando falhar, a função devolve 1. Na primeira subida, isso para o
# container; mas o "restart: unless-stopped" sobe ele de novo, a imagem acha o
# banco já criado e NÃO roda este script outra vez: o banco fica no ar sem as
# permissões reduzidas. Por isso o guia pede o SHOW GRANTS depois do deploy.
# Rodado à mão, o status de saída é 1.

_bandejao_sql() {
    MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot
}

# Texto entre aspas simples no SQL: dobra as aspas e as barras invertidas.
_bandejao_literal() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"
}

# Nome entre crases no SQL: dobra as crases.
_bandejao_identificador() {
    printf '%s' "$1" | sed -e 's/`/``/g'
}

_bandejao_erro() {
    printf '%s\n' "[bandejao] ERRO: $1 Confira a senha de root no .env.db e se o banco já terminou de subir (docker compose ps), e rode o script de novo." >&2
}

_bandejao_usuarios() {
    _bandejao_app=$(_bandejao_literal "$MYSQL_USER")
    _bandejao_banco=$(_bandejao_identificador "$MYSQL_DATABASE")
    # No GRANT de banco, o "_" e o "%" são curingas: "ru_db" valeria também
    # para "ruXdb". Os GRANTs usam o nome escapado (ru\_db), que vale só
    # para o banco da aplicação (#250).
    _bandejao_banco_escapado=$(printf '%s' "$_bandejao_banco" | sed -e 's/[_%]/\\&/g')
    # A imagem dá o ALL com só o "_" escapado, e as versões do script antes
    # da #250 davam os GRANTs sem escape. Para rodar de novo num banco que já
    # existe, antes do GRANT novo: o usuário da aplicação perde o que tiver
    # nos três nomes (o da imagem, o sem escape e o escapado); o papel, que a
    # imagem não toca, perde só o GRANT sem escape.
    _bandejao_banco_imagem=$(printf '%s' "$_bandejao_banco" | sed -e 's/_/\\_/g')

    printf '%s\n' "[bandejao] Ajustando as permissões de '$MYSQL_USER' no banco '$MYSQL_DATABASE'."
    _bandejao_sql <<SQL || { _bandejao_erro "as permissões de '$MYSQL_USER' não foram ajustadas."; return 1; }
REVOKE IF EXISTS ALL PRIVILEGES ON \`${_bandejao_banco_imagem}\`.* FROM '${_bandejao_app}'@'%';
REVOKE IF EXISTS ALL PRIVILEGES ON \`${_bandejao_banco}\`.* FROM '${_bandejao_app}'@'%';
REVOKE IF EXISTS ALL PRIVILEGES ON \`${_bandejao_banco_escapado}\`.* FROM '${_bandejao_app}'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON \`${_bandejao_banco_escapado}\`.* TO '${_bandejao_app}'@'%';

CREATE ROLE IF NOT EXISTS 'equipe_moderacao';
REVOKE IF EXISTS SELECT, INSERT, UPDATE, DELETE ON \`${_bandejao_banco}\`.* FROM 'equipe_moderacao';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`${_bandejao_banco_escapado}\`.* TO 'equipe_moderacao';
SQL

    if [ -z "$DB_EQUIPE_USER" ] || [ -z "$DB_EQUIPE_PASSWORD" ]; then
        printf '%s\n' "[bandejao] AVISO: DB_EQUIPE_USER ou DB_EQUIPE_PASSWORD faltando no .env.db; o usuário da equipe não foi criado. Preencha o .env.db e rode: docker compose up -d --force-recreate --wait db && docker compose exec db sh /docker-entrypoint-initdb.d/10-usuarios.sh" >&2
        return 0
    fi

    _bandejao_usuario_equipe=$(_bandejao_literal "$DB_EQUIPE_USER")
    _bandejao_senha_equipe=$(_bandejao_literal "$DB_EQUIPE_PASSWORD")
    printf '%s\n' "[bandejao] Criando o usuário da equipe '$DB_EQUIPE_USER'."
    _bandejao_sql <<SQL || { _bandejao_erro "o usuário da equipe '$DB_EQUIPE_USER' não foi criado."; unset _bandejao_senha_equipe; return 1; }
CREATE USER IF NOT EXISTS '${_bandejao_usuario_equipe}'@'%' IDENTIFIED BY '${_bandejao_senha_equipe}';
ALTER USER '${_bandejao_usuario_equipe}'@'%' IDENTIFIED BY '${_bandejao_senha_equipe}';
GRANT 'equipe_moderacao' TO '${_bandejao_usuario_equipe}'@'%';
SET DEFAULT ROLE 'equipe_moderacao' TO '${_bandejao_usuario_equipe}'@'%';
SQL
    unset _bandejao_usuario_equipe _bandejao_senha_equipe
}

_bandejao_usuarios
