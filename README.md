

# Bandejão

> PWA que reúne cardápio, avaliações das refeições, previsão de fila e gamificação dos Restaurantes Universitários (RU) da Universidade de Brasília.

Projeto do **Grupo 6 (G6)** na disciplina **Métodos de Desenvolvimento de Software (MDS)**, do curso de Engenharia de Software da Faculdade de Ciências e Tecnologias em Engenharia (FCTE/UnB), semestre 2026/2, com orientação da Profa. Carla Silva Rocha Aguiar.

🍽️ **Aplicação:** https://bandejaounb.com.br

📘 **Documentação completa:** https://unb-mds.github.io/2026-2-Bandejao-UnB/

📖 **Guia do usuário:** https://unb-mds.github.io/2026-2-Bandejao-UnB/#/guia-do-usuario

✉️ **Contato da equipe:** equipe@bandejaounb.com.br

---

## Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Releases e funcionalidades](#releases-e-funcionalidades)
- [Quem pode usar](#quem-pode-usar)
- [Privacidade e dados pessoais](#privacidade-e-dados-pessoais)
- [Onde o Bandejão está publicado](#onde-o-bandejão-está-publicado)
- [Operação em produção](#operação-em-produção)
- [Guia do usuário](#guia-do-usuário)
- [Documentação](#documentação)
- [Tecnologias](#tecnologias)
- [Qualidade, testes e CI](#qualidade-testes-e-ci)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Como rodar o projeto localmente](#como-rodar-o-projeto-localmente)
- [Como abrir a documentação](#como-abrir-a-documentação)
- [Como contribuir](#como-contribuir)
- [Uso de IA no projeto](#uso-de-ia-no-projeto)
- [Equipe](#equipe)

---

## Sobre o projeto

O cardápio oficial do RU da UnB é publicado em formato de planilha/PDF, o que dificulta a leitura. Além disso, a lotação do RU não segue um padrão fixo e não existe um canal para os frequentadores darem feedback sobre as refeições. O resultado é tempo perdido em filas, dificuldade de quem tem restrição alimentar ou alergia para saber o que pode comer e falta de previsibilidade para quem tem a agenda apertada.

O **Bandejão** centraliza essas informações em um único lugar, a **tela do campus**:

- cardápio diário e semanal por campus, extraído automaticamente do PDF do RU, com filtros de marcadores alimentares e de dieta aplicados no backend;
- avaliações das refeições (1 a 5 estrelas e comentário) feitas pelos próprios usuários;
- previsão do horário de pico da fila, em faixas de 15 minutos, calculada a partir dos check-ins da comunidade confirmados por GPS;
- gamificação para incentivar as contribuições: pontos por check-in e avaliação, patente e ranking semestral opcional por campus.

O cardápio, a previsão de pico e o ranking podem ser consultados por qualquer pessoa, sem cadastro. A conta, criada com matrícula ou SIAPE/matrícula funcional, é necessária para avaliar refeições, fazer check-in e acumular pontos.

**Campi atendidos:** Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa. O Restaurante Executivo do Campus Darcy Ribeiro está fora do escopo.

O Bandejão **não é um site oficial da UnB nem do RU**: é feito pela comunidade acadêmica para a própria comunidade e usa dados públicos e oficiais, como o PDF do cardápio publicado pelo RU.

## Releases e funcionalidades

| Release | Data | Conteúdo |
|---|---|---|
| **[R1 — MVP (protótipo)](https://github.com/unb-mds/2026-2-Bandejao-UnB/releases/tag/release-1)** | 28/09/2026 | Protótipo **somente de frontend**, com dados fixos: cardápio por campus, dia e refeição; filtros de marcadores e de dieta; avaliações de exemplo e campo demonstrativo de avaliação; identidade visual. Acompanha a documentação inicial (requisitos e arquitetura). |
| **R2 — Produto completo** | 25/11/2026 | Entrega final, em produção em `bandejaounb.com.br`: cadastro com matrícula/SIAPE, login com e-mail institucional e senha ([ADR 0016](docs/arquitetura/adr/0016-login-com-email-institucional.md)), confirmação de e-mail com reenvio do link, encerramento de sessão e aviso de privacidade com registro do aceite · tela do campus reunindo cardápio, avaliações, previsão e check-in · leitura automatizada do PDF do cardápio, com descoberta do PDF de cada campus na página do RU ([ADR 0014](docs/arquitetura/adr/0014-descoberta-do-pdf-de-cada-campus.md)) e alerta por e-mail em caso de falha · cardápio servido pela API com filtros no backend · avaliação de refeições · check-in confirmado por GPS · previsão de pico em quatro níveis (vazia, curta, moderada, longa) · pontos por contribuição, patente, tela "Meu progresso" e ranking semestral opcional por campus · PWA instalável e responsivo (celular e desktop) · canal de contato. |

Dos extras planejados para a R2, entrou a consulta dos **indicadores de adesão** por SQL (BD-E5). Os demais extras (pergunta de saída da fila e espera estimada, recuperação de senha pelo site, detecção automática do campus, cardápio da semana seguinte, histórico de refeições anteriores, ícones de marcadores nos pratos e sequência semanal) não entraram e seguem no backlog, junto com a Bandeja de Ouro, o nível da fila agora (RF14), a notificação push (RF23) e os demais itens de gamificação (RF28 a RF32). Enquanto a recuperação de senha não existe, o pedido é feito pelo e-mail da equipe.

O detalhamento, com itens por frente, critérios de pronto, Definition of Done e os marcos da R2 (M1 em 07/11, M2 com check-in em produção em 10/11, M3 em 14/11, M4 com os obrigatórios completos em 18/11 e pronto para os usuários em 22/11), está no [Backlog do produto](https://unb-mds.github.io/2026-2-Bandejao-UnB/#/requisitos/backlog). O andamento de cada sprint está nas [Reviews de sprint](https://unb-mds.github.io/2026-2-Bandejao-UnB/#/reviews-sprints/README).

## Quem pode usar

| Perfil | Como acessa | O que pode fazer |
|---|---|---|
| **Visitante** | Sem login | Consultar o cardápio, as avaliações, a previsão de pico e o ranking |
| **Estudante** | Conta com matrícula (extraída do e-mail `@aluno.unb.br`) | Tudo do visitante, avaliar refeições, fazer check-in e participar da gamificação |
| **Professor/Servidor** | Conta com SIAPE/matrícula funcional e e-mail `@unb.br` | Tudo do visitante, avaliar refeições, fazer check-in e participar da gamificação |

Terceirizados e demais frequentadores sem matrícula ou SIAPE usam o Bandejão como visitantes.

## Privacidade e dados pessoais

O [Aviso de privacidade](docs/requisitos/aviso-de-privacidade.md) explica, conforme a LGPD, quais dados o Bandejão guarda, para quê, por quanto tempo e como pedir acesso, correção ou exclusão. Em resumo:

- sem conta, nenhum dado que identifique a pessoa é guardado: o campus, os filtros e a localização usada para abrir a tela do campus ficam só no aparelho ([ADR 0009](docs/arquitetura/adr/0009-deteccao-de-campus-no-aparelho.md));
- a sessão usa cookie HttpOnly ([ADR 0007](docs/arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md)) e a participação no ranking é opcional;
- os check-ins têm retenção limitada, e os backups do banco são apagados depois de 7 dias, para que os dados de uma conta excluída também saiam deles;
- os pedidos sobre os dados vão para **equipe@bandejaounb.com.br**.

## Onde o Bandejão está publicado

A aplicação está no ar em **https://bandejaounb.com.br**, numa máquina virtual Linux da Azure (Azure for Students), com Docker Compose: o Caddy (HTTPS com Let's Encrypt e o PWA), o backend Django com Gunicorn e o MySQL 8.4. Os e-mails saem pelo Brevo ([ADR 0012](docs/arquitetura/adr/0012-hospedagem-e-servico-de-email.md)).

Todo merge na `main` vai para produção sozinho, pelo deploy contínuo ([`deploy.yml`](.github/workflows/deploy.yml)): depois que o CI do commit passa, o GitHub Actions entra na VM com uma chave restrita a um único comando, faz backup do banco, avança a `main` até o commit, reconstrói os containers (as migrações rodam na subida do backend) e confere se o PWA e a API respondem pela internet. Não há rollback automático: se algo falhar, o log mostra o commit anterior e o backup para voltar à mão. Os detalhes (serviços, configuração, deploy automático, banco, tarefas periódicas e cuidados) estão no guia de [Deploy de produção](docs/deploy/deploy-producao.md).

Fluxo das branches até a produção:

```
feature/… ──PR──▶ develop ──PR de release (merge commit)──▶ main ──deploy automático──▶ bandejaounb.com.br
                     │
                     └──▶ site da documentação (GitHub Pages)
```

Correções feitas direto na `main` voltam para a `develop` por PR.

O site do GitHub Pages, citado abaixo, é **só a documentação** do projeto, e não a aplicação.

## Operação em produção

| Assunto | Como funciona | Documento |
|---|---|---|
| **Tarefas periódicas** | Cron na VM: leitura do cardápio a cada 3 horas, limpeza de sessões (diária) e de cadastros não confirmados (de hora em hora) e retenção dos registros da fila (diária), com logs em `/var/log/bandejao/` | [Deploy de produção](docs/deploy/deploy-producao.md) |
| **Backup do banco** | Um `mysqldump` por dia (03h45 de Brasília), conferido e comprimido, guardado por 7 dias, com script de teste de restauração | [Backup do banco](docs/deploy/backup-banco.md) |
| **Disponibilidade** | Dois monitores do UptimeRobot, a cada 5 minutos, de fora da VM. Meta do RNF02: 95% do tempo das 7h às 19h30 nos dias com refeição | [Monitor de disponibilidade](docs/operacao/monitor-disponibilidade.md) · [Relatório parcial](docs/operacao/relatorio-disponibilidade-parcial.md) |
| **Moderação** | Sem tela administrativa: a equipe modera por consultas diretas ao banco, com usuário próprio e papel restrito, sempre em transação ([ADR 0004](docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md)) | [Roteiro de moderação](docs/operacao/roteiro-de-moderacao.md) |
| **Indicadores de adesão** | Quatro consultas SQL manuais (RNF09), testadas no CI em SQLite e MySQL | [Indicadores de adesão (BD-E5)](docs/arquitetura/banco-de-dados/indicadores-adesao-bd-e5.md) |

## Guia do usuário

Como usar o Bandejão (primeiros passos, instalação na tela inicial, cardápio e filtros, previsão da fila, avaliação, check-in, pontos e ranking, privacidade, solução de problemas e perguntas frequentes): [Guia do usuário](docs/guia-do-usuario.md), também no [site da documentação](https://unb-mds.github.io/2026-2-Bandejao-UnB/#/guia-do-usuario).

## Documentação

Toda a documentação fica na pasta [`docs/`](docs/) e é publicada automaticamente no **GitHub Pages** (Docsify): **https://unb-mds.github.io/2026-2-Bandejao-UnB/**

| Seção | Conteúdo |
|---|---|
| **Uso e contribuição** | [Guia do usuário](docs/guia-do-usuario.md) · [Como contribuir](CONTRIBUTING.md) · [Registro de uso de IA](AI-USAGE.md) |
| **Requisitos** | [Documento de Visão](docs/requisitos/documento-de-visao-bandejao.md) · [Documento de Requisitos](docs/requisitos/documento-de-requisitos-bandejao.md) · [Glossário do domínio](docs/requisitos/CONTEXT-DOMINIO.md) · [Backlog do produto](docs/requisitos/backlog.md) · [Aviso de privacidade](docs/requisitos/aviso-de-privacidade.md) |
| **Arquitetura (C4)** | [Níveis 1 e 2](docs/arquitetura/c4-niveis-1-2.md) · Backend: [Nível 3](docs/arquitetura/backend/c4-nivel-3-backend.md) e Nível 4 ([cadastro/autenticação](docs/arquitetura/backend/c4-nivel-4-cadastro-autenticacao.md), [exposição do cardápio](docs/arquitetura/backend/c4-nivel-4-exposicao-cardapio.md), [leitor do cardápio](docs/arquitetura/backend/c4-nivel-4-leitor-cardapio.md), [avaliação](docs/arquitetura/backend/c4-nivel-4-avaliacao.md), [fila](docs/arquitetura/backend/c4-nivel-4-fila.md), [gamificação](docs/arquitetura/backend/c4-nivel-4-gamificacao.md)) · [Teste do leitor do PDF (BE-04)](docs/arquitetura/backend/teste-leitor-pdf-be-04.md) · Banco de dados: [Nível 3](docs/arquitetura/banco-de-dados/C4-nivel-3-banco-de-dados-bandejao.md), [Nível 4](docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md), [Índices da previsão e do ranking (BD-10)](docs/arquitetura/banco-de-dados/indices-bd10.md) e [Indicadores de adesão (BD-E5)](docs/arquitetura/banco-de-dados/indicadores-adesao-bd-e5.md) · [Front-end](docs/arquitetura/front-end/c4-niveis-3-4-frontend-bandejao.md) |
| **Decisões de arquitetura (ADRs)** | [0001 Stack do backend](docs/arquitetura/adr/0001-escolha-stack-backend.md) · [0002 Matrícula e apelido extraídos do e-mail](docs/arquitetura/adr/0002-matricula-apelido-extraidos-do-email.md) · [0003 Leitor de PDF como módulo do backend](docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md) · [0004 Acesso direto da equipe ao banco](docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md) · [0005 Filtros no backend](docs/arquitetura/adr/0005-filtros-de-marcador-e-dieta-no-backend.md) · [0006 Alerta de falha do leitor por e-mail](docs/arquitetura/adr/0006-alerta-de-falha-do-leitor-por-email.md) · [0007 Sessão por cookie HttpOnly](docs/arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md) · [0008 Matrícula/SIAPE em texto claro](docs/arquitetura/adr/0008-matricula-siape-em-texto-claro.md) · [0009 Detecção de campus no aparelho](docs/arquitetura/adr/0009-deteccao-de-campus-no-aparelho.md) · [0010 Nível por chegadas com espera estimada](docs/arquitetura/adr/0010-nivel-por-chegadas-com-espera-estimada.md) · [0011 Contadores de gamificação além da retenção](docs/arquitetura/adr/0011-contadores-de-gamificacao-alem-da-janela-de-retencao.md) · [0012 Hospedagem na Azure e e-mail pelo Brevo](docs/arquitetura/adr/0012-hospedagem-e-servico-de-email.md) · [0013 Estratégia de testes e portas de qualidade](docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md) · [0014 Descoberta do PDF de cada campus](docs/arquitetura/adr/0014-descoberta-do-pdf-de-cada-campus.md) · [0015 Permissões de agentes de IA](docs/arquitetura/adr/0015-permissoes-de-agentes-de-ia-no-repositorio.md) · [0016 Login com e-mail institucional](docs/arquitetura/adr/0016-login-com-email-institucional.md) |
| **Contrato da API** | [OpenAPI v1](backend/openapi.yaml) (gerado com `drf-spectacular` e conferido nos testes do backend) |
| **Qualidade** | [Plano de testes](docs/qualidade/plano-de-testes.md) · [Teste de carga (BD-14)](docs/qualidade/teste-de-carga-bd14.md) · [Checklist de qualidade do front (FE-16)](docs/qualidade/checklist-qualidade-front.md) |
| **Deploy** | [Deploy de produção](docs/deploy/deploy-producao.md) · [Backup do banco](docs/deploy/backup-banco.md) |
| **Operação** | [Roteiro de moderação](docs/operacao/roteiro-de-moderacao.md) · [Monitor de disponibilidade](docs/operacao/monitor-disponibilidade.md) · [Relatório parcial de disponibilidade](docs/operacao/relatorio-disponibilidade-parcial.md) |
| **Gestão do projeto** | [Atas de reunião](docs/atas-reunioes/README.md) · [Reviews de sprint](docs/reviews-sprints/README.md) ([review e retrospectiva das sprints](docs/reviews-sprints/sprint_review_mds.md)) |
| **Estudos** | [Resumos semanais da equipe](docs/estudos/) |
| **Skills de IA** | [Como e quando o grupo usa cada skill](SKILLS/USO-DAS-SKILLS.md) · [Lista das skills](SKILLS/README.md) |
| **Design** | [Double Diamond no Figma](https://www.figma.com/board/acRlPdHQYnCuHXr8dEDaF7/Template-MDS--c%C3%B3pia-limpa---c%C3%B3pia-) (cópia local em [`double-diamond/`](double-diamond/)) |

### Como o site da documentação é publicado

O GitHub Pages publica a pasta `docs/` da branch **`develop`**. Todo merge na `develop` atualiza o site da documentação em 1 a 2 minutos. Commits em outras branches só aparecem depois do merge. A aplicação é publicada de outro jeito, a partir da `main` (ver [Onde o Bandejão está publicado](#onde-o-bandejão-está-publicado)).

Para incluir uma página nova: crie o arquivo `.md` dentro de `docs/` e adicione o link em [`docs/_sidebar.md`](docs/_sidebar.md). Diagramas em blocos ` ```mermaid ` são renderizados automaticamente. Para linkar um PDF, use `[texto](caminho/arquivo.pdf ':ignore')`.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Frontend | Vue 3.5, Vite 8, Vue Router 5 e Pinia 4 (PWA, mobile-first e responsivo), sem framework de CSS |
| Backend | Python 3.14, Django 6.1, Django REST Framework 3.18 e `drf-spectacular` para o contrato OpenAPI ([ADR 0001](docs/arquitetura/adr/0001-escolha-stack-backend.md)) |
| Leitor do cardápio | `pdfplumber`, como módulo do app `cardapio` ([ADR 0003](docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md)); `requests` e `beautifulsoup4` para descobrir o PDF de cada campus na página do RU ([ADR 0014](docs/arquitetura/adr/0014-descoberta-do-pdf-de-cada-campus.md)) |
| Banco de dados | SQLite em desenvolvimento, MySQL 8.4 (`utf8mb4`) em produção e no CI |
| Hospedagem | Máquina virtual Linux da Azure (Azure for Students) com Docker Compose, Caddy 2.11 e Gunicorn; e-mails pelo Brevo ([ADR 0012](docs/arquitetura/adr/0012-hospedagem-e-servico-de-email.md)); disponibilidade acompanhada pelo UptimeRobot |
| CI/CD | GitHub Actions: CI do backend e do frontend, testes de ponta a ponta, teste de carga, mutação semanal e deploy automático pela `main` |
| Documentação | Docsify + Mermaid, publicado no GitHub Pages |
| Testes e qualidade | Frontend: Vitest, `@vue/test-utils`, `fast-check`, StrykerJS, Playwright, ESLint, Oxlint e Prettier. Backend: pytest, pytest-django, pytest-cov, `hypothesis`, `time-machine`, `mutmut`, Ruff, Bandit, pip-audit e Semgrep. Carga: Locust ([ADR 0013](docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md)) |

## Qualidade, testes e CI

As metas de qualidade valem para o backend e para o frontend e são conferidas no CI: um PR que não as cumpre não entra na `develop` ([Plano de testes](docs/qualidade/plano-de-testes.md), [ADR 0013](docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md)).

| Métrica | Meta |
|---|---|
| Cobertura de linhas (módulos críticos) | **≥ 70%** (no backend, linhas e ramos juntos) |
| Escore de mutação (módulos críticos) | **≥ 50%** (`mutmut` no backend, StrykerJS no frontend) |
| Teste de sabotagem | **100%** dos módulos críticos |
| Achados críticos ou altos em SAST e dependências | **0 em aberto** (Bandit, Semgrep, pip-audit, `npm audit`) |

Workflows do GitHub Actions ([`.github/workflows/`](.github/workflows/)):

| Workflow | Quando roda | O que faz |
|---|---|---|
| [Backend CI](.github/workflows/backend-ci.yml) | Push e PR para `develop` e `main` | Ruff, testes em SQLite e em MySQL 8.4 com cobertura, Bandit, pip-audit, Semgrep, migrações pendentes e mutação incremental nos PRs |
| [Frontend CI](.github/workflows/frontend-ci.yml) | Push e PR para `develop` e `main` | Lint, testes com cobertura, build, `npm audit` e mutação incremental nos PRs |
| [E2E](.github/workflows/e2e.yml) | Push e PR | Testes de ponta a ponta com Playwright na pilha real (PWA, API, MySQL e Mailpit), no celular e no desktop |
| [Teste de carga](.github/workflows/carga.yml) | PR para `develop` que muda o teste de carga, ou manual | Locust sobre o cardápio e a previsão (RNF01: p95 até 3 s com até 500 usuários simultâneos) |
| [Mutação semanal](.github/workflows/backend-mutacao-semanal.yml) (back e [front](.github/workflows/frontend-mutacao-semanal.yml)) | Domingos, ou manual | Mutação completa dos módulos críticos na `develop` |
| [Deploy](.github/workflows/deploy.yml) | Push na `main` | Espera o CI do commit e faz o deploy na VM de produção |

## Estrutura do repositório

```
.
├── backend/              # API Django/DRF
│   ├── config/           # settings, urls, wsgi/asgi, formato de erros e logs
│   ├── apps/             # um app por recurso: cadastro, cardapio (com o leitor), avaliacao, fila, gamificacao
│   ├── tests/            # testes de estrutura, contrato da API, segurança, deploy e banco
│   ├── carga/            # teste de carga com Locust (BD-14)
│   ├── scripts/          # mutação incremental
│   ├── Dockerfile
│   └── openapi.yaml      # contrato OpenAPI v1
├── frontend/             # PWA em Vue 3 + Vite (views, components, stores, router, services)
│   ├── e2e/              # testes de ponta a ponta (Playwright) e a pilha Docker usada por eles
│   └── Dockerfile        # build do PWA servido pelo Caddy
├── db/                   # configuração do MySQL e criação dos usuários do banco
├── deploy/               # scripts de produção: deploy contínuo, cron e backup do banco
├── docker-compose.yml    # serviços de produção: db, backend e caddy
├── Caddyfile             # HTTPS, PWA e proxy para a API
├── docs/                 # documentação publicada no GitHub Pages (Docsify)
│   ├── requisitos/       # Visão, Requisitos, glossário, backlog e aviso de privacidade
│   ├── arquitetura/      # C4 (níveis 1 a 4), banco de dados e ADRs
│   ├── qualidade/        # plano de testes, teste de carga e checklist do front
│   ├── deploy/           # deploy de produção e backup do banco
│   ├── operacao/         # moderação e monitoramento da disponibilidade
│   ├── atas-reunioes/    # atas em PDF
│   ├── reviews-sprints/  # reviews e retrospectivas das sprints
│   └── estudos/          # resumos semanais de estudo
├── double-diamond/       # cópia do board do Figma (Double Diamond)
├── SKILLS/               # instruções de apoio usadas pela equipe com assistentes de IA
├── AI-USAGE.md           # registro do uso de IA por tarefa/PR
├── CONTEXT.md            # glossário do domínio usado com os agentes de IA
├── CONTRIBUTING.md       # guia de contribuição
└── .github/              # templates de issue e de pull request e workflows de CI/CD
```

## Como rodar o projeto localmente

**Pré-requisitos:** Git, Python 3.14, Node `^22.18.0` ou `>=24.12.0` e, para os testes de ponta a ponta, Docker.

```bash
git clone https://github.com/unb-mds/2026-2-Bandejao-UnB.git
cd 2026-2-Bandejao-UnB
```

**Backend** (API em http://localhost:8000/api/, com SQLite e os e-mails no terminal):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py loaddata campi marcadores
python manage.py runserver
```

**Frontend** (PWA em http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

Por padrão, o `npm run dev` usa um backend simulado, que não precisa do Django. Para usar a API real, crie `frontend/.env.local` com `VITE_USE_MOCK=false`. Os comandos do CI, a conta de demonstração, os testes de ponta a ponta e a mutação estão no guia [Como contribuir](CONTRIBUTING.md) e no [README do frontend](frontend/README.md).

## Como abrir a documentação

**Online:** abra https://unb-mds.github.io/2026-2-Bandejao-UnB/. Não precisa instalar nada.

**Localmente** (para conferir uma alteração em `docs/` antes do merge), rode na raiz do repositório:

```bash
python -m http.server 3000 --directory docs
```

e abra http://localhost:3000.

## Como contribuir

O passo a passo completo está no guia **[Como contribuir](CONTRIBUTING.md)**: como preparar o ambiente, o fluxo de branches (Gitflow a partir da `develop`), o TDD com o teste antes do código, os commits em Conventional Commits, os pull requests com a Definition of Done, a revisão de código e as regras de uso de IA.

Resumo: crie a branch a partir da `develop` (`feature/…`, `fix/…`, `docs/…` ou `chore/…`), escreva o teste antes do código e abra um PR pequeno para a `develop`, com o [template de PR](.github/PULL_REQUEST_TEMPLATE.md), o CI verde e a revisão de alguém de outra frente. Bugs e novas tarefas entram pelos [templates de issue](.github/ISSUE_TEMPLATE/).

## Uso de IA no projeto

A equipe usa assistentes de IA como apoio, sempre com revisão humana e com os testes como evidência:

- cada uso relevante fica registrado em [`AI-USAGE.md`](AI-USAGE.md), com a tarefa/PR, a ferramenta, o apoio recebido, a validação e a revisão humana;
- as permissões dos agentes de IA no repositório estão na [ADR 0015](docs/arquitetura/adr/0015-permissoes-de-agentes-de-ia-no-repositorio.md);
- as skills usadas pelo grupo, e quando usar cada uma, estão em [`SKILLS/`](SKILLS/README.md).

## Equipe

**Grupo 6 — Estudantes de Engenharia de Software (FCTE/UnB)**

- Alana Cristyna Feitosa Dias
- Álvaro Bento Moura da Silva
- Corina Xavier Carneiro
- Cristiano Monteiro Coelho Lacerda Póvoas
- Josué Xavier Carneiro
- Luís Felipe Albuquerque Fernandes

**Orientadora:** Profa. Carla Silva Rocha Aguiar
