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
- **`.env.db`**: só a senha do root do MySQL, que vai apenas para o container
  `db`. Assim, o backend, que recebe o tráfego da internet, não a conhece.

Conteúdo do `.env` (a explicação de cada variável está no
`backend/.env.example`):

| Variável | Valor |
|---|---|
| `SECRET_KEY` | chave do Django (segredo) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `bandejaounb.com.br,www.bandejaounb.com.br` |
| `CSRF_TRUSTED_ORIGINS` | `https://bandejaounb.com.br,https://www.bandejaounb.com.br` |
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

Sem `DEBUG`, as três variáveis de e-mail são obrigatórias, e o backend não
sobe sem elas. Enquanto o Brevo não estiver configurado, troque as três por
`EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`. Com isso, os
e-mails aparecem no `docker compose logs backend`.

Estes são os nomes que o `settings.py` lê hoje. O PR de produção da dupla do
banco troca alguns deles pelos nomes `DJANGO_*` (BD-05) e atualiza o
`backend/.env.example`. Nesse caso, basta renomear as linhas no `.env`.

Conteúdo do `.env.db`:

```env
MYSQL_ROOT_PASSWORD=<senha do root do MySQL>
```

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
- `https://bandejaounb.com.br/admin/` abre o login do admin, com CSS.

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
  `mysql_dados` vazio. Se um script mudar depois, aplique-o na mão:

  ```bash
  docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' < db/init/<script>.sql
  ```

  A outra saída é recriar o volume com `docker compose down -v`, que **apaga
  todos os dados do banco** e só deve ser usada antes de haver dados reais (e
  depois de um backup). O backup diário do banco é a BD-15.
- **Não apague o volume `caddy_dados`.** Ele guarda os certificados, e o
  Let's Encrypt limita quantos certificados o mesmo domínio pode pedir por
  semana.
- O banco e o Gunicorn não têm portas publicadas. A equipe acessa o banco por
  túnel SSH (ADR 0004); nunca adicione `ports` ao serviço `db`.
- Antes de desligar ou apagar recursos na Azure, lembre que o crédito é
  limitado: discos, IPs e VMs de teste esquecidos consomem o crédito (ADR
  0012).
