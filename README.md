# Bandejão

> PWA que reúne cardápio, avaliações das refeições e previsão de fila dos Restaurantes Universitários (RU) da Universidade de Brasília.

Projeto do **Grupo 6 (G6)** na disciplina **Métodos de Desenvolvimento de Software (MDS)**, do curso de Engenharia de Software da Faculdade de Ciências e Tecnologias em Engenharia (FCTE/UnB), semestre 2026/2, com orientação da Profa. Carla Silva Rocha Aguiar.

📘 **Documentação completa:** https://unb-mds.github.io/2026-2-Bandejao-UnB/

---

## Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Releases e funcionalidades](#releases-e-funcionalidades)
- [Quem pode usar](#quem-pode-usar)
- [Documentação](#documentação)
- [Tecnologias](#tecnologias)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Como abrir a documentação](#como-abrir-a-documentação)
- [Como contribuir](#como-contribuir)
- [Equipe](#equipe)

---

## Sobre o projeto

O cardápio oficial do RU da UnB é publicado em formato de planilha/PDF, o que dificulta a leitura. Além disso, a lotação do RU não segue um padrão fixo e não existe um canal para os frequentadores darem feedback sobre as refeições. O resultado é tempo perdido em filas, dificuldade de quem tem restrição alimentar ou alergia para saber o que pode comer e falta de previsibilidade para quem tem a agenda apertada.

O **Bandejão** centraliza essas informações em um único lugar:

- cardápio diário e semanal por campus, extraído automaticamente do PDF do RU, com filtros de marcadores alimentares e de dieta;
- avaliações das refeições (1 a 5 estrelas e comentário) feitas pelos próprios usuários;
- previsão do horário de pico da fila, calculada a partir dos check-ins da comunidade.

O cardápio e a previsão de pico podem ser consultados por qualquer pessoa, sem cadastro. A conta, criada com matrícula ou SIAPE/matrícula funcional, é necessária para avaliar refeições e fazer check-in.

**Campi atendidos:** Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa. O Restaurante Executivo do Campus Darcy Ribeiro está fora do escopo.

## Releases e funcionalidades

| Release | Data | Conteúdo |
|---|---|---|
| **R1** | 28/09/2026 | Protótipo **somente de frontend**, com dados fixos: cardápio por campus, dia e refeição; filtros de marcadores e de dieta; avaliações de exemplo e campo demonstrativo de avaliação; identidade visual. Acompanha a documentação inicial (requisitos e arquitetura). |
| **R2 — Produto completo** | 25/11/2026 | Entrega final, com **todos os requisitos (RF01 a RF18)** operando em produção: cadastro e login por matrícula/SIAPE com confirmação de e-mail e recuperação de senha · leitura automatizada do PDF do cardápio · filtros aplicados no backend · ícones de marcadores nos pratos · cardápio da semana seguinte · avaliação de refeições · histórico de refeições anteriores · check-in confirmado por GPS · previsão de pico em quatro níveis (vazia, curta, moderada, longa) · nível da fila agora · PWA instalável. |

O detalhamento, com histórias de usuário, critérios de aceite, ordem de execução e o marco de check-in em produção em 03/11/2026, está no [Backlog do produto](https://unb-mds.github.io/2026-2-Bandejao-UnB/#/requisitos/backlog).

## Quem pode usar

| Perfil | Como acessa | O que pode fazer |
|---|---|---|
| **Visitante** | Sem login | Consultar o cardápio e a previsão de pico |
| **Estudante** | Conta com matrícula (extraída do e-mail `@aluno.unb.br`) | Tudo do visitante, avaliar refeições e fazer check-in |
| **Professor/Servidor** | Conta com SIAPE/matrícula funcional e e-mail `@unb.br` | Tudo do visitante, avaliar refeições e fazer check-in |

Terceirizados e demais frequentadores sem matrícula ou SIAPE usam o Bandejão como visitantes.

## Documentação

Toda a documentação fica na pasta [`docs/`](docs/) e é publicada automaticamente no **GitHub Pages** (Docsify): **https://unb-mds.github.io/2026-2-Bandejao-UnB/**

| Seção | Conteúdo |
|---|---|
| **Requisitos** | [Documento de Visão](docs/requisitos/documento-de-visao-bandejao.md) · [Documento de Requisitos](docs/requisitos/documento-de-requisitos-bandejao.md) · [Glossário do domínio](docs/requisitos/CONTEXT-DOMINIO.md) · [Backlog do produto](docs/requisitos/backlog.md) |
| **Arquitetura (C4)** | [Níveis 1 e 2](docs/arquitetura/c4-niveis-1-2.md) · Backend: [Nível 3](docs/arquitetura/backend/c4-nivel-3-backend.md) e Nível 4 ([cadastro/autenticação](docs/arquitetura/backend/c4-nivel-4-cadastro-autenticacao.md), [exposição do cardápio](docs/arquitetura/backend/c4-nivel-4-exposicao-cardapio.md), [leitor do cardápio](docs/arquitetura/backend/c4-nivel-4-leitor-cardapio.md), [avaliação](docs/arquitetura/backend/c4-nivel-4-avaliacao.md), [fila](docs/arquitetura/backend/c4-nivel-4-fila.md)) · [Banco de dados](docs/arquitetura/banco-de-dados/C4-niveis-3-4-banco-de-dados-bandejao.md) · [Front-end](docs/arquitetura/front-end/c4-niveis-3-4-frontend-bandejao.md) |
| **Decisões de arquitetura (ADRs)** | [0001 Stack do backend](docs/arquitetura/adr/0001-escolha-stack-backend.md) · [0002 Matrícula e apelido extraídos do e-mail](docs/arquitetura/adr/0002-matricula-apelido-extraidos-do-email.md) · [0003 Leitor de PDF como módulo do backend](docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md) · [0004 Acesso direto da equipe ao banco](docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md) · [0005 Filtros no backend](docs/arquitetura/adr/0005-filtros-de-marcador-e-dieta-no-backend.md) · [0006 Alerta de falha do leitor por e-mail](docs/arquitetura/adr/0006-alerta-de-falha-do-leitor-por-email.md) · [0007 Sessão por cookie HttpOnly](docs/arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md) · [0008 Matrícula/SIAPE em texto claro](docs/arquitetura/adr/0008-matricula-siape-em-texto-claro.md) |
| **Gestão do projeto** | [Atas de reunião](docs/atas-reunioes/README.md) · [Reviews de sprint](docs/reviews-sprints/README.md) |
| **Estudos** | [Resumos semanais da equipe](docs/estudos/) |
| **Design** | [Double Diamond no Figma](https://www.figma.com/board/acRlPdHQYnCuHXr8dEDaF7/Template-MDS--c%C3%B3pia-limpa---c%C3%B3pia-) (cópia local em [`double-diamond/`](double-diamond/)) |
| **Protótipo**| [protótipo] (https://pin-round-77758179.figma.site/) |

### Como o site é publicado

O GitHub Pages publica a pasta `docs/` da branch **`develop`**. Todo merge na `develop` atualiza o site em 1 a 2 minutos. Commits em outras branches só aparecem depois do merge.

Para incluir uma página nova: crie o arquivo `.md` dentro de `docs/` e adicione o link em [`docs/_sidebar.md`](docs/_sidebar.md). Diagramas em blocos ` ```mermaid ` são renderizados automaticamente. Para linkar um PDF, use `[texto](caminho/arquivo.pdf ':ignore')`.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Frontend | Vue 3, Vite, Vue Router (PWA, mobile-first) |
| Backend | Python, Django, Django REST Framework ([ADR 0001](docs/arquitetura/adr/0001-escolha-stack-backend.md)) |
| Banco de dados | SQLite em desenvolvimento, MySQL em produção |
| Documentação | Docsify + Mermaid, publicado no GitHub Pages |
| Testes e qualidade | Vitest, ESLint, Oxlint e Prettier no frontend; testes do Django no backend |

## Estrutura do repositório

```
.
├── backend/            # API Django/DRF
│   ├── config/         # settings, urls, wsgi/asgi
│   └── apps/           # um app por recurso: usuarios, cardapio, avaliacoes, status, core
├── frontend/           # PWA em Vue 3 + Vite (views, router, assets)
├── docs/               # documentação publicada no GitHub Pages (Docsify)
│   ├── requisitos/     # Visão, Requisitos, glossário e backlog
│   ├── arquitetura/    # C4 (níveis 1 a 4) e ADRs
│   ├── atas-reunioes/  # atas em PDF
│   ├── reviews-sprints/
│   └── estudos/        # resumos semanais de estudo
├── double-diamond/     # cópia do board do Figma (Double Diamond)
├── SKILLS/             # instruções de apoio usadas pela equipe com assistentes de IA
└── .github/            # templates de issue e de pull request
```

## Como abrir a documentação

**Online:** abra https://unb-mds.github.io/2026-2-Bandejao-UnB/. Não precisa instalar nada.

**Localmente** (para conferir uma alteração em `docs/` antes do merge), rode na raiz do repositório:

```bash
python -m http.server 3000 --directory docs
```

e abra http://localhost:3000.

## Como contribuir

- **Branches (Gitflow):** o desenvolvimento acontece na **`develop`**, e a `main` recebe as entregas. Crie sua branch a partir da `develop` com um prefixo: `feature/…`, `fix/…`, `docs/…` ou `chore/…`.
- **Commits:** mensagens no padrão *Conventional Commits*, em português (ex.: `feat: adiciona filtro de dieta`, `docs: atualiza o backlog`).
- **Pull requests:** sempre para a `develop`, usando o [template de PR](.github/PULL_REQUEST_TEMPLATE.md) e referenciando a issue.
- **Issues:** use os templates de [história de usuário](.github/ISSUE_TEMPLATE/historia_usuario.yml), [tarefa](.github/ISSUE_TEMPLATE/tarefa.yml) ou [bug](.github/ISSUE_TEMPLATE/bug_report.yml). Os IDs e labels seguem o [Backlog do produto](docs/requisitos/backlog.md).
- **Vocabulário:** use os termos do [glossário do domínio](docs/requisitos/CONTEXT-DOMINIO.md) no código e nos textos (ex.: *Marcador*, e não "alérgeno").
- **Decisões de arquitetura:** registre como nova ADR em `docs/arquitetura/adr/` e adicione ao menu do site.

## Equipe

**Grupo 6 — Estudantes de Engenharia de Software (FCTE/UnB)**

- Alana Cristyna Feitosa Dias
- Álvaro Bento Moura da Silva
- Corina Xavier Carneiro
- Cristiano Monteiro Coelho Lacerda Póvoas
- Josué Xavier Carneiro
- Luís Felipe Albuquerque Fernandes

**Orientadora:** Profa. Carla Silva Rocha Aguiar
