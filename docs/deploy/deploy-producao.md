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

Na primeira subida, o banco está vazio. Carregue os dados fixos (os 5
campi e os 10 marcadores); sem eles, a API responde `[]` e não há campus
para o check-in. Rode só nessa primeira vez: se for repetido depois, o
comando regrava os campi e os marcadores com os valores da fixture e desfaz
o que tiver sido ajustado no banco (como as coordenadas medidas em campo, BD-06):

```bash
docker compose exec backend python manage.py loaddata campi marcadores
```

### 4. Conferir

- `https://bandejaounb.com.br` abre o PWA, com cadeado no navegador;
- `https://www.bandejaounb.com.br` redireciona para o endereço sem `www`;
- `https://bandejaounb.com.br/api/campi/` responde a lista dos 5 campi;
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

O `check --deploy` do Django também deve mostrar só os avisos de HSTS
(`security.W004`, deixado de fora de propósito) e de `SECURE_SSL_REDIRECT`
(`security.W008`, o Caddy já redireciona):

```bash
docker compose exec backend python manage.py check --deploy
```

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
por SSH" das ADRs 0004, 0008 e 0012 é entrar na VM pelo SSH, com a própria
chave, e abrir o cliente dentro do container, com o próprio usuário de banco:

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

### Conexão com o banco (TLS)

O item BD-05 do backlog (`docs/requisitos/backlog.md`) pede a conexão com o
banco criptografada se a hospedagem oferecer (ADR 0008). A ADR 0008 registra
que a conexão da aplicação com o banco não sai do servidor, que a porta do
banco não é exposta à internet e que o acesso da equipe passa pelo SSH, que é
criptografado. Na prática, a equipe entra na VM pelo SSH e abre o cliente
dentro do container, sem túnel até o banco (ver "Acesso da equipe").

**Situação conferida na VM em 19/11/2026: a conexão do backend com o MySQL não
usava TLS** (o `Ssl_cipher` da conexão do backend veio vazio). Por padrão, o
MySQL 8.4 gera um certificado próprio na primeira subida, mas o backend não
pede TLS: o `OPTIONS` do banco em `settings.py` não tem `ssl`/`ssl_mode`, e a
biblioteca cliente da imagem do backend (`libmariadb3`, usada pelo
`mysqlclient`) conectou sem TLS. Isso fica dentro do que a ADR 0008 considera
suficiente: o tráfego entre o backend e o banco fica na rede interna do
Compose, dentro da VM, e a porta do banco não é publicada (o serviço `db` do
`docker-compose.yml` não tem `ports`).

A exigência de TLS (`REQUIRE SSL` no usuário) não foi ligada. Com o backend sem
pedir TLS, o servidor recusaria a conexão e derrubaria o backend. Ligar o TLS
exige configurar `ssl` no `OPTIONS`, decidir como tratar o certificado
autoassinado do MySQL e só então pôr `REQUIRE SSL` no usuário; seria uma
decisão nova (com uma ADR), e não um ajuste do guia. Para quem for ligar:

- o `REQUIRE SSL` vai só no `DB_USER`, gravado no `db/init/10-usuarios.sh`; um
  `ALTER USER` feito à mão se perde se o volume `mysql_dados` for recriado;
- o certificado gerado pelo MySQL é emitido por uma CA própria (`ca.pem`, no
  volume do banco) e tem um nome diferente de `db`, então a verificação do nome
  do servidor falharia; é preciso usar esse `ca.pem` no backend sem verificar o
  nome, ou gerar um certificado com o nome `db`.

A `libmariadb3` não tem versão fixa no `backend/Dockerfile` (vem do Debian da
imagem `python:3.14-slim`), então um rebuild pode mudar o comportamento.
Confira de novo depois de reconstruir a imagem do backend:

```bash
docker compose exec backend python manage.py shell --no-imports -c "from django.db import connection; c = connection.cursor(); c.execute(\"SHOW SESSION STATUS LIKE 'Ssl_cipher'\"); print(c.fetchone())"
```

O `--no-imports` evita a linha de importações automáticas do `shell` do
Django; sem ele, a tupla é a última linha da saída. Um nome de cifra (como
`TLS_AES_256_GCM_SHA384`) indica conexão cifrada; um valor vazio
(`('Ssl_cipher', '')`, o resultado de 19/11/2026) indica conexão sem TLS.

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

Se o merge mudou algum arquivo de `deploy/cron/`, reinstale-o como em
[Tarefas periódicas](#tarefas-periódicas-cron).

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

## Deploy do M2 (FE-06)

O M2 é o check-in funcionando em produção (MC-01). O PWA com o check-in
(FE-05, #141) já está na `develop`. O deploy é o mesmo da seção
[Atualizar](#atualizar), feito na `develop`, que é a branch que a VM roda até
a release; depois da release, passa a ser a `main` (ver
[Clonar o repositório](#1-clonar-o-repositório)).

O build de produção nunca usa o servidor simulado: no `vite build` o Vite
fixa `import.meta.env.DEV` em `false`, e o `if (import.meta.env.DEV)` de
`requisitarSimulado` tira o simulado do bundle. O job `build (front)` do CI
confere isso com um `grep` no `dist/`. A regra de quando ligar o simulado fica
em `deveUsarSimulacao` (`frontend/src/services/apiClient.js`), e o teste do
`apiClient` confere essa regra com e sem `VITE_USE_MOCK`.

### Antes de subir

- CI verde na `develop` (backend e frontend).
- Campi carregados (`/api/campi/` devolve os 5, ver
  [Validação em produção](#validação-em-produção-20112026)). O
  `POST /api/checkins/` recebe o `id` do campus; sem os campi, todo check-in
  volta `400 dados_invalidos`.

### Roteiro de ponta a ponta (BD-08)

Em um celular com a localização ligada, dentro do RU do Gama, num horário de
refeição:

1. Abrir `https://bandejaounb.com.br` e escolher o campus **Gama**.
2. Criar a conta com um e-mail institucional real.
3. Abrir o link de confirmação que chegou no e-mail (Brevo).
4. Entrar com o e-mail e a senha.
5. Abrir **Fila** e tocar em **Estou no RU**.
6. Dar ciência ao aviso de privacidade e permitir a localização.
7. Conferir "Check-in confirmado".
8. Recarregar a página e tocar de novo em **Estou no RU**: deve aparecer
   "Você já fez check-in nesta refeição hoje.".
9. Conferir no banco que o check-in foi gravado (campus 3, refeição e data de
   hoje):

   ```bash
   docker compose exec backend python manage.py shell -c "from apps.fila.models import Checkin; print(Checkin.objects.order_by('-id').values().first())"
   ```

10. Conferir que a localização não foi guardada (RI09): nem o `Checkin` nem a
    `TentativaCheckin` têm campo de latitude ou longitude, e elas não aparecem
    em `docker compose logs --tail 100 backend`.

Anote a data e o resultado de cada passo na issue #142 (FE-06) e na #148
(BD-08). Se um passo falhar, os logs ficam em
`docker compose logs --tail 100 backend`.

## Tarefas periódicas (cron)

As tarefas periódicas são comandos do Django chamados pelo **cron da VM**
(ADRs 0003, 0007, 0012 e 0014; BD-07). Os arquivos ficam em `deploy/cron/`:

| Arquivo | Vai para | O que faz |
|---|---|---|
| `bandejao` | `/etc/cron.d/bandejao` | A agenda das tarefas |
| `rodar-comando.sh` | (fica no repositório) | Roda o comando no container do backend com tempo limite, grava o log, avisa as falhas no syslog e impede duas execuções do mesmo comando ao mesmo tempo |
| `logrotate` | `/etc/logrotate.d/bandejao` | Uma cópia do log por semana, cerca de 5 semanas guardadas |

| Comando | Quando (Brasília) | Para quê |
|---|---|---|
| `excluir_cadastros_pendentes` | de hora em hora | Apaga o cadastro sem confirmação nem reenvio há mais de 24 h (RF02.3) |
| `ler_cardapio` | de 3 em 3 horas, todos os dias | Lê o PDF do cardápio de cada campus (ADR 0014) |
| `clearsessions` | todo dia, 03h15 | Apaga as sessões expiradas do Django (ADR 0007) |
| `desvincular_registros_fila` | todo dia, 03h30 | Retira a conta dos registros de fila com mais de 4 semanas (RNF07.3) |

Os horários do arquivo estão em **UTC**, o fuso da VM (Brasília é UTC-3).
A linha do `ler_cardapio` fica **comentada** até o merge do #218 (BE-12), que
cria o comando. Depois dele, alguém tira o `# ` da linha no `bandejao` (o
teste do cron cobra isso) e reinstala o arquivo.

### Instalar

Uma vez, na VM, da pasta do repositório:

```bash
cd ~/2026-2-Bandejao-UnB
timedatectl | grep "Time zone"     # deve ser UTC (Etc/UTC)
id -nG azureuser | grep -w docker  # o azureuser precisa estar no grupo docker
sudo install -d -o azureuser -g azureuser -m 750 /var/log/bandejao
sudo install -m 644 -o root -g root deploy/cron/bandejao /etc/cron.d/bandejao
sudo install -m 644 -o root -g root deploy/cron/logrotate /etc/logrotate.d/bandejao
systemctl is-active cron           # deve responder "active"
```

O cron lê o `/etc/cron.d/` sozinho, sem reiniciar. Ele ignora o arquivo se o
dono não for o root ou se outro usuário puder escrever nele: por isso o
`install` com `-o root` e `-m 644`. As tarefas rodam como `azureuser`, que
usa o Docker sem root.

Se a VM não estiver em UTC, ajuste as horas do `bandejao` antes de instalar.

### Conferir

Rode cada comando uma vez à mão, pelo mesmo script do cron, **como
`azureuser` e sem `sudo`**, e veja o log:

```bash
sh deploy/cron/rodar-comando.sh clearsessions
sh deploy/cron/rodar-comando.sh excluir_cadastros_pendentes
tail -n 5 /var/log/bandejao/*.log
```

Com `sudo`, o log e a trava passam a ser do root, e o cron do `azureuser` não
consegue mais gravar: a tarefa para e só deixa o erro no syslog (status 73).
Se isso acontecer, devolva os arquivos ao `azureuser`:
`sudo chown azureuser:azureuser /var/log/bandejao/*`.

Cada execução grava no log do comando:

- `início`;
- a saída do comando: o resumo e, em falha, a mensagem de erro com o
  traceback, sem e-mail, matrícula nem nome;
- `fim: status N`.

| Status | Quer dizer |
|---|---|
| 0 | Sucesso |
| 75 | Pulado: a execução anterior do mesmo comando ainda estava rodando |
| 124 | Tempo esgotado: o comando passou de 2 h e foi encerrado dentro do container (ou o cliente do `docker` travou por mais de 130 min) |
| 137 | Encerrado à força (KILL): não saiu depois do tempo esgotado, ou faltou memória |
| 73 | O log ou a trava não podem ser gravados (o script rodou com `sudo`?) |
| 1 ou 2 | Erro do próprio script antes do log (pasta, `mkdir`, `cd`, uso ou nome inválido) |
| outro | Erro do comando; a mensagem fica nas linhas de cima do log |

Os status 1, 2 e 73 saem antes do log, então a execução não aparece no
arquivo do comando. Se o log não tiver a execução esperada, veja o
`journalctl -t bandejao-cron`.

Todo status diferente de 0 também vai para o syslog, com a tag
`bandejao-cron`. O status 75 vai como aviso, e os outros, como erro. A VM não
manda e-mail, então **a conferência é manual**: uma vez por semana, ou depois
de cada deploy, veja os erros dos últimos dias.

```bash
journalctl -t bandejao-cron --since "7 days ago"   # falhas e pulos das tarefas
journalctl -u cron --since today | tail -n 20      # cada disparo do cron
ls -l /var/log/bandejao/
sudo logrotate -d /etc/logrotate.d/bandejao        # simula a rotação, sem mexer
```

Depois do #218 (BE-12), as falhas de leitura do PDF também avisam a equipe
por e-mail (ADR 0006), com limite de avisos por dia, desde que o
`EMAIL_EQUIPE` esteja no `.env`. Um erro que derrube o comando, o tempo
esgotado e as falhas das outras tarefas só aparecem no syslog e no log.

### Mudar ou desligar

Se o `deploy/cron/bandejao` ou o `logrotate` mudar num merge, repita o
`sudo install` correspondente depois do `git pull`. O `rodar-comando.sh` é
usado direto do repositório e não precisa ser reinstalado.

Para desligar todas as tarefas, apague o arquivo:
`sudo rm /etc/cron.d/bandejao`.

## Ver logs

```bash
docker compose logs -f              # todos os serviços
docker compose logs -f backend      # só o Django/Gunicorn
docker compose logs --tail 100 caddy
```

Cada container guarda no máximo 3 arquivos de 10 MB de log.

As tarefas do cron têm o próprio log, um arquivo por comando, em
`/var/log/bandejao/` (ver [Tarefas periódicas](#tarefas-periódicas-cron)).

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

## Validação em produção (20/11/2026)

Conferido na VM depois do primeiro deploy. Os itens do banco, do
`check --deploy` e do e-mail estão na entrada "BD-05 — Banco, settings de produção e e-mail"
do `AI-USAGE.md`.

| Item | Resultado |
|---|---|
| Serviços `db`, `backend` e `caddy` | `Up`; `db` e `backend` `healthy` |
| `https://bandejaounb.com.br` | `HTTP/2 200`, com HTTPS |
| `https://www.bandejaounb.com.br` | `301` para o domínio sem `www` |
| `/api/campi/` | JSON com os 5 campi (depois do `loaddata`) |
| Porta 3306 pela internet | Recusada (o NSG só libera 22, 80 e 443) |
| `.env` e `.env.db` | Permissão `600` |
| Reinício da VM (`sudo reboot`) | Os três serviços voltaram sozinhos (`restart: unless-stopped`), e os dados do banco continuaram |
| IP real atrás do Caddy (`NUM_PROXIES = 1`) | De uma rede, o 11º pedido de reenvio deu `429`. De outra rede (a própria VM), o pedido seguinte deu `200`: o limite conta cada IP separado |