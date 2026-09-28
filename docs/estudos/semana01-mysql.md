# Semana 01 — Banco de Dados em Produção com Django

**Integrante:** Luis Felipe
**Semana:** 01
**Data:** 05/09/2026
**Área:** Banco de Dados
**Tags:** `mysql` `django` `python` `backend` `produção` `sprint1`

---

## Resumo

Durante a Sprint 1, nosso foco principal no backend foi evoluir o estudo inicial de banco de dados da Sprint 0 para um cenário real de produção. Trabalhamos na conexão prática entre nossa aplicação construída em Python (Django) e o MySQL. O objetivo foi deixar de lado o ambiente isolado e teórico para entender como manter, atualizar e proteger um banco de dados que já possui dados reais e ativos circulando.

## Aplicação no projeto

Esta etapa de configuração é a espinha dorsal para o armazenamento do projeto. Definir o MySQL como banco de produção em vez de um banco local padrão garante que o sistema suporte conexões reais de forma estável. Além disso, as práticas de manutenção estudadas agora são o que garantirão que, à medida que formos desenvolvendo novas funcionalidades ao longo do semestre, a estrutura de tabelas possa ser alterada sem apagar ou corromper os registros que já estiverem salvos.

## Principais conceitos / como usar

- **Configurando a conexão (`DATABASES`):** para que o Django pare de usar o banco nativo e comece a conversar com o MySQL, precisamos configurar a constante `DATABASES` dentro do arquivo `settings.py`. Alteramos o `ENGINE` para o módulo do MySQL e informamos as credenciais de acesso, como `NAME` (nome do banco), `USER`, `PASSWORD`, `HOST` e `PORT`. Isso cria a comunicação direta entre a nossa API e o servidor do banco.

  ```python
  # settings.py
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.mysql',
          'NAME': 'ru_db',
          'USER': 'ru_user',
          'PASSWORD': 'senha_segura',
          'HOST': '127.0.0.1',
          'PORT': '3306',
      }
  }
  ```

  Em produção, credenciais como `USER` e `PASSWORD` não devem ficar escritas diretamente no `settings.py`. O padrão é lê-las de variáveis de ambiente (ex. com `django-environ` ou `python-decouple`), mantendo um arquivo `.env` fora do controle de versão.

- **Migrations seguras em produção:** no desenvolvimento local, se algo der errado, é comum deletar o banco e recriar. Em um ambiente de produção, isso é inaceitável pois significa perda de dados reais. `makemigrations` gera os arquivos de migração a partir das mudanças feitas nos models; `migrate` de fato aplica essas alterações no schema do banco. É vital revisar o código gerado pelo Django antes de aplicar a migração no servidor para garantir que nenhuma coluna seja apagada acidentalmente e saber como gerenciar valores padrão (*default*) ao criar novos campos em tabelas já preenchidas.
- **Revertendo uma migration:** se uma migration aplicada causar problema em produção, é possível voltar o banco para um estado anterior com `python manage.py migrate app_name 000X` (número da migration anterior). Nem toda migration é reversível automaticamente — remoção de coluna, por exemplo, perde dado ao reverter.
- **Rotinas de backup e restore:** a segurança das informações exige rotinas de prevenção. Aprendemos como gerar um "retrato" do estado atual do banco fazendo um backup simples, geralmente exportando toda a estrutura e dados para um arquivo `.sql` com a ferramenta `mysqldump`. Da mesma forma, entendemos o processo de *restore*, que consiste em pegar esse arquivo `.sql` e importá-lo de volta para o MySQL, recuperando os dados em caso de falhas críticas. Em produção real, esse backup costuma ser automatizado — por *cron job* agendado no servidor, ou por backups gerenciados diretamente pelo provedor de nuvem (AWS RDS, Google Cloud SQL etc.) — em vez de rodado manualmente.

## Fontes e materiais usados

- Documentação oficial do Django: [configuração de bancos de dados (MySQL)](https://docs.djangoproject.com/en/6.0/ref/settings/#databases)
- Documentação oficial do Django: [Migrations](https://docs.djangoproject.com/en/6.0/topics/migrations/)
- Documentação oficial do MySQL: [uso do programa `mysqldump` para backups](https://dev.mysql.com/doc/en/using-mysqldump.html)
- Playlist "Curso de SQL com MySQL (Completo)", de Otávio Miranda: https://www.youtube.com/playlist?list=PLbIBj8vQhvm2WT-pjGS5x7zUzmh4VgvRk
- Playlist "Curso de Banco de Dados MySQL", de Gustavo Guanabara (Curso em Vídeo): https://www.youtube.com/playlist?list=PLHz_AreHm4dkBs-795Dsgvau_ekxg8g1r
- Artigos e fóruns sobre boas práticas de manutenção de schemas relacionais em produção