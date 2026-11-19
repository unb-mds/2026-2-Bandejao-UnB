#!/bin/sh
# Usuários do MySQL de produção (BD-05, ADR 0004 e 0008).
#
# Roda sozinho na PRIMEIRA subida do container db, com o volume vazio, logo
# depois de a imagem criar o banco (MYSQL_DATABASE) e o usuário da aplicação
# (MYSQL_USER). Para aplicar de novo num banco que já existe:
#
#   docker compose exec db sh /docker-entrypoint-initdb.d/10-usuarios.sh
#
# Pode rodar quantas vezes for preciso: cada comando confere o que já existe.
#
# 1. Usuário da aplicação: a imagem dá a ele ALL PRIVILEGES no banco. O script
#    deixa só o que o Django usa: ler e gravar dados e, nas migrations que o
#    entrypoint.sh aplica a cada subida, criar e alterar tabelas e índices.
#    Nada fora do banco da aplicação (nenhum GRANT em *.*).
# 2. Papel equipe_moderacao: ler e alterar dados para a moderação (ADR 0004),
#    sem mudar a estrutura das tabelas, que é das migrations.
# 3. Usuário da equipe (DB_EQUIPE_USER, do .env.db), com esse papel. A ADR 0012
#    pede um usuário por membro: os demais são criados à mão, como no guia de
#    deploy (docs/deploy/deploy-producao.md).
#
# As senhas vêm do ambiente do container (.env e .env.db) e nunca do Git.
#
# A imagem do MySQL roda este arquivo com "source" quando ele não é
# executável. Por isso tudo fica dentro de funções com prefixo, e o script não
# usa "exit": um erro aqui pararia a primeira subida do banco.

_bandejao_sql() {
    MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot
}

# Texto entre aspas simples no SQL: dobra as aspas e as barras invertidas.
_bandejao_literal() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"
}

_bandejao_usuarios() {
    printf '%s\n' "[bandejao] Ajustando as permissões de '$MYSQL_USER' no banco '$MYSQL_DATABASE'."
    _bandejao_sql <<SQL
REVOKE IF EXISTS ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* FROM '${MYSQL_USER}'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';

CREATE ROLE IF NOT EXISTS 'equipe_moderacao';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`${MYSQL_DATABASE}\`.* TO 'equipe_moderacao';
SQL

    if [ -z "$DB_EQUIPE_USER" ] || [ -z "$DB_EQUIPE_PASSWORD" ]; then
        printf '%s\n' "[bandejao] AVISO: DB_EQUIPE_USER ou DB_EQUIPE_PASSWORD faltando no .env.db; o usuário da equipe não foi criado. Preencha e rode este script de novo (docs/deploy/deploy-producao.md)." >&2
        return 0
    fi

    _bandejao_usuario_equipe=$(_bandejao_literal "$DB_EQUIPE_USER")
    _bandejao_senha_equipe=$(_bandejao_literal "$DB_EQUIPE_PASSWORD")
    printf '%s\n' "[bandejao] Criando o usuário da equipe '$DB_EQUIPE_USER'."
    _bandejao_sql <<SQL
CREATE USER IF NOT EXISTS '${_bandejao_usuario_equipe}'@'%' IDENTIFIED BY '${_bandejao_senha_equipe}';
ALTER USER '${_bandejao_usuario_equipe}'@'%' IDENTIFIED BY '${_bandejao_senha_equipe}';
GRANT 'equipe_moderacao' TO '${_bandejao_usuario_equipe}'@'%';
SET DEFAULT ROLE 'equipe_moderacao' TO '${_bandejao_usuario_equipe}'@'%';
SQL
    unset _bandejao_usuario_equipe _bandejao_senha_equipe
}

_bandejao_usuarios
