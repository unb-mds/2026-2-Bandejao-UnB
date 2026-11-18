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
- `.env`, na raiz, **só na VM**.

## Infraestrutura

| Item | Valor |
|---|---|
| Assinatura | Azure for Students, dono: Luís Felipe (LuisFelipe311), válida até 14/11/2027 |
| VM | `vm-bandejao`, grupo `rg-bandejao`, North Central US, B2as_v2 (2 vCPUs) |
| IP público (estático) | `20.102.232.122` |
| Portas abertas (NSG) | 22, 80 e 443 |
| DNS (Registro.br) | registro A da raiz e CNAME `www` apontando para a VM |
| Orçamento | `orcamento-bandejao`, R$ 550/mês, alertas em 50/80/100% |

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

### 2. Criar o `.env`

Crie o arquivo `.env` na raiz do repositório (ao lado do
`docker-compose.yml`) e restrinja a leitura ao seu usuário:

```bash
nano .env
chmod 600 .env
```

O Compose usa o `.env` para o MySQL e repassa todas as variáveis, com o mesmo
nome, ao backend. Os nomes e a explicação de cada uma estão no
`backend/.env.example`. As variáveis do banco são:

| Variável | Valor |
|---|---|
| `DB_HOST` | `db` (nome do serviço no Compose) |
| `DB_PORT` | `3306` |
| `DB_NAME` | `bandejao` |
| `DB_USER` | usuário da aplicação |
| `DB_PASSWORD` | senha do usuário da aplicação |
| `MYSQL_ROOT_PASSWORD` | senha do root do MySQL |

Gere as senhas e a chave do Django com:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

O `.env` nunca vai para o Git (está no `.gitignore`). Guarde uma cópia das
senhas num lugar seguro da equipe: sem a do root, não dá para administrar o
banco.

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
migrations e inicia o Gunicorn. O Caddy pede o certificado na primeira
requisição a cada domínio.

### 4. Conferir

- `https://bandejaounb.com.br` abre o PWA, com cadeado no navegador;
- `https://www.bandejaounb.com.br` redireciona para o endereço sem `www`;
- `https://bandejaounb.com.br/api/cardapio/` responde JSON;
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
  depois de um backup).
- **Não apague o volume `caddy_dados`.** Ele guarda os certificados, e o
  Let's Encrypt limita quantos certificados o mesmo domínio pode pedir por
  semana.
- O banco e o Gunicorn não têm portas publicadas. A equipe acessa o banco por
  túnel SSH (ADR 0004); nunca adicione `ports` ao serviço `db`.
- Antes de desligar ou apagar recursos na Azure, lembre que o crédito é
  limitado: discos, IPs e VMs de teste esquecidos consomem o crédito (ADR
  0012).
