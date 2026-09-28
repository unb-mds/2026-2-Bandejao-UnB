# SQLite

**Integrante:** Josué Xavier Carneiro
**Semana:** 01
**Data:** 05/09/2026
**Tags:** sqlite, django, docker, banco-de-dados

## Resumo

SQLite é um sistema de gerenciamento de banco de dados leve, na forma de biblioteca que roda localmente e armazena os dados em um único arquivo no disco (`.sqlite3`), sem precisar de servidor externo, configuração de usuários ou instalação separada. É amplamente usado em aplicações mobile, desktop e sistemas embarcados, funciona em diferentes sistemas operacionais e tem uso simples, com pouca complexidade de configuração. Sua principal limitação é não ser recomendado para sistemas com muitos usuários simultâneos, pois trava o arquivo inteiro durante escritas.

## Aplicação no projeto

No projeto, o SQLite é usado como banco de dados padrão em ambiente de desenvolvimento, sendo a opção *out of the box* do Django (configurada em `settings.py`, sem precisar instalar drivers adicionais). Isso permite que qualquer integrante do time rode o projeto localmente sem precisar subir um servidor de banco separado (como seria necessário com PostgreSQL/MySQL), e o arquivo do banco pode ser resetado facilmente durante testes e prototipação. A limitação de concorrência não é um problema nesta fase porque, em desenvolvimento, normalmente só uma ou poucas pessoas acessam o banco por vez. Está prevista a migração para PostgreSQL (ou similar) no ambiente de produção, já que o SQLite trava o arquivo inteiro durante escritas e não seria adequado para múltiplos containers/réplicas acessando o mesmo arquivo simultaneamente.

## Principais conceitos / como usar

- O Django usa um ORM (Object-Relational Mapper): em vez de escrever SQL manualmente, os dados são definidos como classes Python em `models.py`, e o Django traduz isso em SQL por trás dos panos.
- Configuração da conexão em `settings.py`: diferente de bancos cliente-servidor, não há host, porta, usuário ou senha — só `ENGINE` (dialeto do banco) e `NAME` (caminho do arquivo).
- Criação de tabelas via migrations, não SQL direto:
  ```bash
  python manage.py makemigrations   # gera o script da alteração
  python manage.py migrate          # aplica no arquivo .sqlite3
  ```
- Consultas básicas via ORM (equivalentes a SQL puro): `Feedback.objects.create(...)` (INSERT), `Feedback.objects.all()` (SELECT *), `Feedback.objects.filter(...)` (SELECT com WHERE), `obj.save()` após alterar atributos (UPDATE).
- O Django ORM já protege contra SQL Injection automaticamente, sem precisar se preocupar com concatenação de strings.
- **SQLite dentro do Docker (problema da persistência):** containers são efêmeros — ao serem removidos/recriados, o `db.sqlite3` interno se perde junto. A solução é usar **volumes**, que mapeiam uma pasta persistente para dentro do container:
  - *Bind mount* (`.:/app`): mapeia uma pasta real da máquina do dev — bom pra inspecionar o arquivo `.sqlite3` diretamente.
  - *Named volume* (`sqlite_data:/app/data`): o Docker gerencia o armazenamento internamente — mais comum para o arquivo de banco em si.
  - No `settings.py`, o banco deve apontar para dentro da pasta persistida (ex: `BASE_DIR / 'data' / 'db.sqlite3'`).
- **Teste de validação:** rodar `docker-compose up --build`, `migrate`, `createsuperuser`, depois `down` e `up` de novo — se o volume estiver certo, o superusuário criado antes continua existindo.

## Fontes / materiais usados

- Documentação oficial do Django — Databases (seção SQLite notes): https://docs.djangoproject.com/en/stable/ref/databases/#sqlite-notes
- Documentação oficial do Docker — Volumes: https://docs.docker.com/storage/volumes/
- Resumo e tira-dúvidas com Claude
