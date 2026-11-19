# Deploy de produção (BD-05)

Como subir e manter o Bandejão em `https://bandejaounb.com.br`, na VM da
Azure (ADR 0012). Tudo roda com Docker Compose, a partir da raiz do
repositório.

## Visão geral

| Serviço | O que faz | Exposto à internet |
|---|---|---|
| `caddy` | HTTPS automático (Let's Encrypt), serve o build do PWA e encaminha `/api/` e `/admin/` ao backend | Sim, portas 80 e 443 |
| `backend` | Django com Gunicorn. Na subida, roda `migrate` e `collectstatic` | Não |
| `db` | MySQL 8.4, com os dados no volume `mysql_dados` | Não |

Os três serviços têm `restart: unless-stopped`: voltam sozinhos se caírem ou
se a VM reiniciar.

Arquivos envolvidos:

- `docker-compose.yml` e `Caddyfile`, na raiz;
- `backend/Dockerfile` e `backend/entrypoint.sh`;
- `frontend/Dockerfile` (build do PWA dentro da imagem do Caddy);
- `db/init/` (scripts de criação de usuários) e `db/conf.d/` (arquivos `.cnf`
  do MySQL);
- `.env` e `.env.db`, na raiz, **só na VM**.

## Infraestrutura

| Item | Valor |
|---|---|
| Assinatura | Azure for Students do integrante LuisFelipe311 (ADR 0012), válida até 14/11/2027 |
| VM | Linux, 2 vCPUs |
| IP público (estático) | `20.102.232.122` |
| Portas abertas (NSG) | 22, 80 e 443 |
| DNS (Registro.br) | registro A da raiz e CNAME `www` apontando para a VM |
| Orçamento | alerta de orçamento em 50/80/100% do crédito |

Os nomes dos recursos na Azure (grupo, VM, orçamento) ficam com quem tem
acesso à assinatura, e não neste repositório público.

O acesso à VM é por chave SSH, com o usuário `azureuser`, e cada membro usa a
própria chave (ADR 0012). Para ganhar acesso, gere a chave
(`ssh-keygen -t ed25519`) e mande **só a chave pública**
(`~/.ssh/id_ed25519.pub`) a quem já tem acesso. Essa pessoa a acrescenta, na
VM, ao `~/.ssh/authorized_keys` do `azureuser`. Para tirar o acesso de alguém,
basta apagar a linha da chave dessa pessoa nesse arquivo.

## Primeiro deploy

### 1. Clonar o repositório

```bash
ssh azureuser@20.102.232.122
git clone https://github.com/unb-mds/2026-2-Bandejao-UnB.git
cd 2026-2-Bandejao-UnB
```

Em produção vale a branch `main`. Antes da release, pode-se usar a `develop`
(`git checkout develop`).

### 2. Criar o `.env` e o `.env.db`

São dois arquivos na raiz do repositório (ao lado do `docker-compose.yml`),
com leitura só para o seu usuário:

```bash
nano .env
nano .env.db
chmod 600 .env .env.db
```

- **`.env`**: o Compose repassa todas as variáveis dele, com o mesmo nome, ao
  backend. Também usa `DB_NAME`, `DB_USER` e `DB_PASSWORD` para criar o banco
  e o usuário da aplicação na primeira subida do MySQL.
- **`.env.db`**: a senha do root do MySQL e o usuário da equipe, que vão
  apenas para o container `db`. Assim, o backend, que recebe o tráfego da
  internet, não os conhece.

Conteúdo do `.env` (a explicação de cada variável está no
`backend/.env.example`):

| Variável | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | chave do Django (segredo) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `bandejaounb.com.br,www.bandejaounb.com.br` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://bandejaounb.com.br,https://www.bandejaounb.com.br` |
| `URL_DO_PWA` | `https://bandejaounb.com.br` |
| `DB_ENGINE` | `mysql` (sem ela, o Django usa SQLite) |
| `DB_HOST` | `db` (nome do serviço no Compose) |
| `DB_PORT` | `3306` |
| `DB_NAME` | `bandejao` |
| `DB_USER` | usuário da aplicação |
| `DB_PASSWORD` | senha do usuário da aplicação (segredo) |
| `EMAIL_HOST` | `smtp-relay.brevo.com` |
| `EMAIL_HOST_USER` | login SMTP do Brevo |
| `EMAIL_HOST_PASSWORD` | chave SMTP do Brevo (segredo) |
| `EMAIL_PORT` | `587` (já é o padrão) |
| `EMAIL_USE_TLS` | `True` (já é o padrão) |
| `DEFAULT_FROM_EMAIL` | remetente verificado no Brevo |

Sem `DJANGO_DEBUG=True`, as três variáveis do SMTP e o `DEFAULT_FROM_EMAIL`
são obrigatórios, e o backend não sobe sem eles. Também não defina
`EMAIL_BACKEND` no `.env` de produção: com outro backend (o do console, por
exemplo), o cadastro responderia 201, o e-mail nunca sairia e o link de
confirmação iria para o log, então o backend para na subida. Configure o Brevo
antes do deploy (veja [E-mail (Brevo)](#e-mail-brevo)).

Sem `DJANGO_ALLOWED_HOSTS`, o backend também não sobe: o Django responderia
400 a todos os pedidos.

As quatro variáveis do Django têm o prefixo `DJANGO_` desde a BD-05. Num
`.env` mais antigo, com `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` ou
`CSRF_TRUSTED_ORIGINS`, o backend para na subida e o `docker compose logs
backend` mostra o que renomear. Basta acrescentar `DJANGO_` no começo dessas
linhas e recriar o backend (`docker compose up -d --force-recreate backend`).

Conteúdo do `.env.db`:

```env
MYSQL_ROOT_PASSWORD=<senha do root do MySQL>
DB_EQUIPE_USER=<usuário de banco de quem modera>
DB_EQUIPE_PASSWORD=<senha desse usuário>
```

O `DB_EQUIPE_USER` é o primeiro usuário individual da equipe (ADR 0004 e
0012). Os demais membros ganham o seu como em [Banco](#banco), abaixo.

Gere as senhas e a chave do Django com:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Os dois arquivos nunca vão para o Git (estão no `.gitignore`). Guarde uma
cópia das senhas num lugar seguro da equipe: sem a do root, não dá para
administrar o banco.

As senhas do banco só valem na **primeira** subida, quando o volume
`mysql_dados` está vazio. Depois disso, mudar `DB_PASSWORD` ou
`MYSQL_ROOT_PASSWORD` nos arquivos não muda a senha no MySQL. É preciso trocar
também no banco, com `ALTER USER`, e depois recriar o backend.

### 3. Subir

```bash
docker compose up -d --build
```

Na primeira vez o build demora alguns minutos. Depois, acompanhe a subida:

```bash
docker compose ps
docker compose logs -f
```

O `db` fica `healthy` em até um minuto. Só então o `backend` sobe, aplica as
migrations e inicia o Gunicorn. Quando o Gunicorn aceita conexões, o `backend`
fica `healthy`, e o Caddy sobe. O Caddy pede os certificados ao subir, para os
dois domínios do `Caddyfile`. Se o backend não subir, o `docker compose logs
backend` mostra o motivo (por exemplo, uma variável faltando no `.env`).

### 4. Conferir

- `https://bandejaounb.com.br` abre o PWA, com cadeado no navegador;
- `https://www.bandejaounb.com.br` redireciona para o endereço sem `www`;
- `https://bandejaounb.com.br/api/campi/` responde JSON;
- `https://bandejaounb.com.br/admin/` abre o login do admin, com CSS;
- **as permissões do banco foram reduzidas** (obrigatório, veja abaixo).

O `10-usuarios.sh` roda só na primeira subida. Se ele falhar, o container do
banco para, mas o `restart: unless-stopped` sobe ele de novo, a imagem acha o
banco já criado e não roda o script outra vez: o banco fica no ar com o
`DB_USER` em `ALL PRIVILEGES` e sem o usuário da equipe, sem nenhum erro
visível. Confira sempre depois do primeiro deploy (troque `<DB_USER>` pelo
valor do `.env`):

```bash
docker compose logs db | grep bandejao
docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' <<'SQL'
SHOW GRANTS FOR '<DB_USER>'@'%';
SQL
```

O resultado certo tem só `SELECT, INSERT, UPDATE, DELETE, CREATE, DROP,
REFERENCES, INDEX, ALTER` no banco `bandejao`, e nenhum `ALL PRIVILEGES`. Se
aparecer `ALL PRIVILEGES`, ou se o log mostrar `[bandejao] ERRO`, rode o
script à mão, como em [Banco](#banco); ele sai com erro se algo falhar. Antes
de haver dados reais, também dá para apagar o volume e subir de novo (`docker
compose down -v`, que **apaga todo o banco**).

Para criar o superusuário do admin:

```bash
docker compose exec backend python manage.py createsuperuser
```

### 5. Teste de reboot

```bash
sudo systemctl is-enabled docker   # tem que responder "enabled"
sudo reboot
```

Espere uns 2 minutos, entre de novo pelo SSH e confira:

```bash
docker ps
```

Os três containers precisam aparecer como **Up**, e o site precisa abrir sem
nenhum comando manual.

## Banco

O MySQL lê o `db/conf.d/bandejao.cnf`: `utf8mb4` (acentos e emojis) e
isolamento `READ COMMITTED`. Na primeira subida, o `db/init/10-usuarios.sh`
ajusta os usuários:

| Usuário | Permissões | Para quê |
|---|---|---|
| `DB_USER` (aplicação) | `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `INDEX` e `REFERENCES`, só no banco `DB_NAME` | O Django: dados e migrations. A imagem do MySQL dava `ALL PRIVILEGES` a ele, e o script retira o resto |
| papel `equipe_moderacao` | `SELECT`, `INSERT`, `UPDATE` e `DELETE`, só no banco `DB_NAME` | Moderação por acesso direto (ADR 0004), sem mudar a estrutura das tabelas. O `DELETE` é para avaliações; a exclusão de conta é só pelo `RemoverContaCommand`, nunca por `DELETE` direto (o cascade e o `SET NULL` são do ORM) |
| `DB_EQUIPE_USER` | o papel `equipe_moderacao` | O primeiro membro da equipe |

O root só é usado para administrar o banco (criar usuários, por exemplo).

Conferir as permissões e a configuração:

```bash
docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' <<'SQL'
SELECT @@character_set_server, @@collation_server, @@transaction_isolation;
SELECT user, host FROM mysql.user;
SHOW GRANTS FOR 'equipe_moderacao';
SQL
```

Para ver as permissões de um usuário, acrescente `SHOW GRANTS FOR
'<usuário>'@'%';`.

O papel restrito só limita quem entra no banco pelo próprio usuário. Quem tem
acesso ao Docker na VM (o grupo `docker` ou o `sudo`) lê a senha de root com
`docker compose exec db env` e, na prática, tem acesso total ao banco. Por
isso o acesso à VM fica só com quem administra o deploy (#158).

### Acesso da equipe

A porta do banco não é publicada, então não há túnel SSH até ela: o "acesso
por SSH" das ADRs 0004 e 0012 é entrar na VM pelo SSH, com a própria chave, e
abrir o cliente dentro do container, com o próprio usuário de banco:

```bash
docker compose exec db mysql -u <usuário> -p bandejao
```

Para criar o usuário de outro membro (ADR 0004 e 0012: um por pessoa, sem
compartilhar senha), como root:

```sql
CREATE USER '<usuário>'@'%' IDENTIFIED BY '<senha>';
GRANT 'equipe_moderacao' TO '<usuário>'@'%';
SET DEFAULT ROLE 'equipe_moderacao' TO '<usuário>'@'%';
```

Para tirar o acesso: `DROP USER '<usuário>'@'%';`.

Se o `.env.db` ganhar o usuário da equipe depois da primeira subida, ou se o
script mudar, recrie o `db` para ele ler o `.env.db` e rode o script de novo.
O `--wait` espera o banco ficar `healthy`; sem ele, o script pode rodar antes
de o MySQL aceitar conexões. O script pode rodar quantas vezes for preciso e
sai com erro (status 1, com `[bandejao] ERRO`) se algum comando falhar:

```bash
docker compose up -d --force-recreate --wait db
docker compose exec db sh /docker-entrypoint-initdb.d/10-usuarios.sh
```

### Conexão criptografada

O item BD-05 do backlog (`docs/requisitos/backlog.md`) pede a conexão com o
banco criptografada se for viável. A ADR 0008 já considera suficiente que a
conexão da aplicação não saia da VM (rede interna do Compose) e que a da
equipe passe pelo SSH, que é criptografado. Além disso, o MySQL 8.4 gera um
certificado próprio na primeira subida, e o cliente do Django deve usar TLS
quando o servidor oferece (depende do cliente instalado na imagem, ainda não
conferido na VM). Para conferir se a conexão do backend está cifrada:

```bash
docker compose exec backend python manage.py shell -c "from django.db import connection; c = connection.cursor(); c.execute(\"SHOW SESSION STATUS LIKE 'Ssl_cipher'\"); print(c.fetchone())"
```

Um nome de cifra (como `TLS_AES_256_GCM_SHA384`) indica conexão cifrada; um
valor vazio indica conexão sem TLS. A exigência de TLS (`REQUIRE SSL` no
usuário) não foi ligada: o certificado é autoassinado, e o cliente do
container (MariaDB Connector/C) pode recusá-lo, o que derrubaria o backend.

## E-mail (Brevo)

O backend envia pelo SMTP do Brevo, na porta 587 com STARTTLS. Para mandar um
e-mail de teste a um endereço seu:

```bash
docker compose exec backend python manage.py sendtestemail <seu e-mail>
```

Se nada chegar, o `docker compose logs backend` mostra o erro do SMTP. Confira
também, no painel do Brevo, se o remetente (`DEFAULT_FROM_EMAIL`) está
verificado.

## Atualizar

Depois de um merge na branch de produção:

```bash
cd ~/2026-2-Bandejao-UnB
git pull
docker compose up -d --build
```

Só os containers cujas imagens mudaram são recriados. As migrations novas são
aplicadas na subida do backend. Os dados do banco e os certificados ficam nos
volumes e não se perdem.

Se mudar só o `Caddyfile`, basta recarregar o Caddy:

```bash
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Se mudar só o `.env`, recrie o container que usa a variável (o `restart` não
relê o arquivo):

```bash
docker compose up -d --force-recreate backend
```

Se mudar o `.env.db`, recrie o `db` do mesmo jeito
(`docker compose up -d --force-recreate db`).

Lembre que mudar uma senha do banco nos arquivos não muda a senha no MySQL
(ver o passo 2).

Numa VM com um `.env` anterior ao `.env.db`, tire a linha
`MYSQL_ROOT_PASSWORD` do `.env` e passe-a para o `.env.db`. Senão, o backend
continua recebendo a senha do root, porque o `.env` vai inteiro para ele.

## Ver logs

```bash
docker compose logs -f              # todos os serviços
docker compose logs -f backend      # só o Django/Gunicorn
docker compose logs --tail 100 caddy
```

Cada container guarda no máximo 3 arquivos de 10 MB de log.

## Cuidados

- **Scripts de `db/init/` só rodam na primeira subida**, com o volume
  `mysql_dados` vazio. Se um script mudar depois, aplique-o na mão: o
  `10-usuarios.sh` como em [Banco](#banco); um `.sql` com

  ```bash
  docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' < db/init/<script>.sql
  ```

  A outra saída é recriar o volume com `docker compose down -v`, que **apaga
  todos os dados do banco** e só deve ser usada antes de haver dados reais (e
  depois de um backup). O backup diário do banco é a BD-15.
- **Não apague o volume `caddy_dados`.** Ele guarda os certificados, e o
  Let's Encrypt limita quantos certificados o mesmo domínio pode pedir por
  semana.
- O banco e o Gunicorn não têm portas publicadas. A equipe acessa o banco
  entrando na VM pelo SSH e usando o cliente do container (ADR 0004), como em
  [Acesso da equipe](#acesso-da-equipe); nunca adicione `ports` ao serviço
  `db`.
- Antes de desligar ou apagar recursos na Azure, lembre que o crédito é
  limitado: discos, IPs e VMs de teste esquecidos consomem o crédito (ADR
  0012).
