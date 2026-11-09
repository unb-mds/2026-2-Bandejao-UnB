# Bandejão

> PWA que reúne cardápio, avaliações das refeições, previsão de fila e gamificação dos Restaurantes Universitários (RU) da Universidade de Brasília.

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
| **R1 — MVP (protótipo)** | 28/09/2026 | Protótipo **somente de frontend**, com dados fixos: cardápio por campus, dia e refeição; filtros de marcadores e de dieta; avaliações de exemplo e campo demonstrativo de avaliação; identidade visual. Acompanha a documentação inicial (requisitos e arquitetura). |
| **R2 — Produto completo** | 25/11/2026 | Entrega final, em produção em `bandejaounb.com.br`. **Obrigatórios:** cadastro e login por matrícula/SIAPE com confirmação de e-mail, encerramento de sessão e aviso de privacidade · tela do campus reunindo cardápio, avaliações, previsão e check-in · leitura automatizada do PDF do cardápio · cardápio servido pela API com filtros no backend · avaliação de refeições · check-in confirmado por GPS · previsão de pico em quatro níveis (vazia, curta, moderada, longa) · pontos por contribuição, patente e ranking semestral opcional por campus · PWA instalável · canal de contato. **Extras, se houver tempo (em ordem):** pergunta de saída da fila e espera estimada · recuperação de senha · detecção automática do campus · cardápio da semana seguinte · histórico de refeições anteriores · ícones de marcadores nos pratos · sequência semanal. |

Ficam fora da R2 e seguem no backlog: Bandeja de Ouro, nível da fila agora (RF14), notificação push (RF23) e os demais itens de gamificação (RF28 a RF32).

O detalhamento, com itens por frente, critérios de pronto, Definition of Done e os marcos da R2 (M1 em 07/11, M2 com check-in em produção em 10/11, M3 em 14/11, M4 com os obrigatórios completos em 18/11 e pronto para os usuários em 22/11), está no [Backlog do produto](https://unb-mds.github.io/2026-2-Bandejao-UnB/#/requisitos/backlog).

## Quem pode usar

| Perfil | Como acessa | O que pode fazer |
|---|---|---|
| **Visitante** | Sem login | Consultar o cardápio, a previsão de pico e o ranking |
| **Estudante** | Conta com matrícula (extraída do e-mail `@aluno.unb.br`) | Tudo do visitante, avaliar refeições, fazer check-in e participar da gamificação |
| **Professor/Servidor** | Conta com SIAPE/matrícula funcional e e-mail `@unb.br` | Tudo do visitante, avaliar refeições, fazer check-in e participar da gamificação |

Terceirizados e demais frequentadores sem matrícula ou SIAPE usam o Bandejão como visitantes.

## Documentação

Toda a documentação fica na pasta [`docs/`](docs/) e é publicada automaticamente no **GitHub Pages** (Docsify): **https://unb-mds.github.io/2026-2-Bandejao-UnB/**

| Seção | Conteúdo |
|---|---|
| **Requisitos** | [Documento de Visão](docs/requisitos/documento-de-visao-bandejao.md) · [Documento de Requisitos](docs/requisitos/documento-de-requisitos-bandejao.md) · [Glossário do domínio](docs/requisitos/CONTEXT-DOMINIO.md) · [Backlog do produto](docs/requisitos/backlog.md) |
| **Arquitetura (C4)** | [Níveis 1 e 2](docs/arquitetura/c4-niveis-1-2.md) · Backend: [Nível 3](docs/arquitetura/backend/c4-nivel-3-backend.md) e Nível 4 ([cadastro/autenticação](docs/arquitetura/backend/c4-nivel-4-cadastro-autenticacao.md), [exposição do cardápio](docs/arquitetura/backend/c4-nivel-4-exposicao-cardapio.md), [leitor do cardápio](docs/arquitetura/backend/c4-nivel-4-leitor-cardapio.md), [avaliação](docs/arquitetura/backend/c4-nivel-4-avaliacao.md), [fila](docs/arquitetura/backend/c4-nivel-4-fila.md), [gamificação](docs/arquitetura/backend/c4-nivel-4-gamificacao.md)) · [Teste do leitor do PDF (BE-04)](docs/arquitetura/backend/teste-leitor-pdf-be-04.md) · Banco de dados: [Nível 3](docs/arquitetura/banco-de-dados/C4-nivel-3-banco-de-dados-bandejao.md) e [Nível 4](docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md) · [Front-end](docs/arquitetura/front-end/c4-niveis-3-4-frontend-bandejao.md) |
| **Decisões de arquitetura (ADRs)** | [0001 Stack do backend](docs/arquitetura/adr/0001-escolha-stack-backend.md) · [0002 Matrícula e apelido extraídos do e-mail](docs/arquitetura/adr/0002-matricula-apelido-extraidos-do-email.md) · [0003 Leitor de PDF como módulo do backend](docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md) · [0004 Acesso direto da equipe ao banco](docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md) · [0005 Filtros no backend](docs/arquitetura/adr/0005-filtros-de-marcador-e-dieta-no-backend.md) · [0006 Alerta de falha do leitor por e-mail](docs/arquitetura/adr/0006-alerta-de-falha-do-leitor-por-email.md) · [0007 Sessão por cookie HttpOnly](docs/arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md) · [0008 Matrícula/SIAPE em texto claro](docs/arquitetura/adr/0008-matricula-siape-em-texto-claro.md) · [0009 Detecção de campus no aparelho](docs/arquitetura/adr/0009-deteccao-de-campus-no-aparelho.md) · [0010 Nível por chegadas com espera estimada](docs/arquitetura/adr/0010-nivel-por-chegadas-com-espera-estimada.md) · [0011 Contadores de gamificação além da retenção](docs/arquitetura/adr/0011-contadores-de-gamificacao-alem-da-janela-de-retencao.md) · [0012 Hospedagem na Azure e e-mail pelo Brevo](docs/arquitetura/adr/0012-hospedagem-e-servico-de-email.md) · [0013 Estratégia de testes e portas de qualidade](docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md) |
| **Contrato da API** | [OpenAPI v1](backend/openapi.yaml) (gerado com `drf-spectacular` e conferido nos testes do backend) |
| **Qualidade** | [Plano de testes](docs/qualidade/plano-de-testes.md) |
| **Gestão do projeto** | [Atas de reunião](docs/atas-reunioes/README.md) · [Reviews de sprint](docs/reviews-sprints/README.md) |
| **Estudos** | [Resumos semanais da equipe](docs/estudos/) |
| **Design** | [Double Diamond no Figma](https://www.figma.com/board/acRlPdHQYnCuHXr8dEDaF7/Template-MDS--c%C3%B3pia-limpa---c%C3%B3pia-) (cópia local em [`double-diamond/`](double-diamond/)) |

### Como o site é publicado

O GitHub Pages publica a pasta `docs/` da branch **`develop`**. Todo merge na `develop` atualiza o site em 1 a 2 minutos. Commits em outras branches só aparecem depois do merge.

Para incluir uma página nova: crie o arquivo `.md` dentro de `docs/` e adicione o link em [`docs/_sidebar.md`](docs/_sidebar.md). Diagramas em blocos ` ```mermaid ` são renderizados automaticamente. Para linkar um PDF, use `[texto](caminho/arquivo.pdf ':ignore')`.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Frontend | Vue 3, Vite, Vue Router e Pinia (PWA, mobile-first) |
| Backend | Python 3.14, Django, Django REST Framework e `drf-spectacular` para o contrato OpenAPI ([ADR 0001](docs/arquitetura/adr/0001-escolha-stack-backend.md)) |
| Leitor do cardápio | `pdfplumber`, como módulo do app `cardapio` ([ADR 0003](docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md)) |
| Banco de dados | SQLite em desenvolvimento, MySQL 8 (`utf8mb4`) em produção |
| Hospedagem | Máquina virtual Linux da Azure (Azure for Students) com Docker Compose, Caddy e Gunicorn; e-mails pelo Brevo ([ADR 0012](docs/arquitetura/adr/0012-hospedagem-e-servico-de-email.md)) |
| Documentação | Docsify + Mermaid, publicado no GitHub Pages |
| Testes e qualidade | Vitest, ESLint, Oxlint e Prettier no frontend; pytest, pytest-django, pytest-cov, Ruff, Bandit, pip-audit e Semgrep no backend, rodando no GitHub Actions com cobertura mínima de 70% ([ADR 0013](docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md)) |

## Estrutura do repositório

```
.
├── backend/            # API Django/DRF
│   ├── config/         # settings, urls, wsgi/asgi, formato de erros
│   ├── apps/           # um app por recurso: cadastro, cardapio (com o leitor), avaliacao, fila, gamificacao
│   ├── tests/          # testes de estrutura, contrato da API e segurança
│   └── openapi.yaml    # contrato OpenAPI v1
├── frontend/           # PWA em Vue 3 + Vite (views, components, stores, router, services)
├── docs/               # documentação publicada no GitHub Pages (Docsify)
│   ├── requisitos/     # Visão, Requisitos, glossário e backlog
│   ├── arquitetura/    # C4 (níveis 1 a 4) e ADRs
│   ├── qualidade/      # plano de testes
│   ├── atas-reunioes/  # atas em PDF
│   ├── reviews-sprints/
│   └── estudos/        # resumos semanais de estudo
├── double-diamond/     # cópia do board do Figma (Double Diamond)
├── SKILLS/             # instruções de apoio usadas pela equipe com assistentes de IA
└── .github/            # templates de issue e de pull request e workflow de CI do backend
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
- **TDD:** o teste entra num commit antes do código (vermelho → verde → refatorar), conforme o [Plano de testes](docs/qualidade/plano-de-testes.md).
- **Pull requests:** sempre para a `develop`, pequenos, usando o [template de PR](.github/PULL_REQUEST_TEMPLATE.md) e referenciando a issue. O PR só entra com o CI verde e revisado por alguém de outra frente, seguindo a Definition of Done do [Backlog do produto](docs/requisitos/backlog.md).
- **Contrato da API:** se um endpoint mudar, atualize o [`backend/openapi.yaml`](backend/openapi.yaml) no mesmo PR.
- **Issues:** use os templates de [história de usuário](.github/ISSUE_TEMPLATE/historia_usuario.yml), [tarefa](.github/ISSUE_TEMPLATE/tarefa.yml) ou [bug](.github/ISSUE_TEMPLATE/bug_report.yml). Os IDs (`BD-`, `BE-`, `FE-`, `QA-`, `DOC-`) e labels seguem o [Backlog do produto](docs/requisitos/backlog.md).
- **Vocabulário:** use os termos do [glossário do domínio](docs/requisitos/CONTEXT-DOMINIO.md) e os nomes da arquitetura (C4) no código e nos textos (ex.: *Marcador*, e não "alérgeno").
- **Decisões de arquitetura:** registre como nova ADR em `docs/arquitetura/adr/` e adicione ao menu do site. Se a implementação divergir do C4, atualize o documento de arquitetura no mesmo PR.

## Equipe

**Grupo 6 — Estudantes de Engenharia de Software (FCTE/UnB)**

- Alana Cristyna Feitosa Dias
- Álvaro Bento Moura da Silva
- Corina Xavier Carneiro
- Cristiano Monteiro Coelho Lacerda Póvoas
- Josué Xavier Carneiro
- Luís Felipe Albuquerque Fernandes

**Orientadora:** Profa. Carla Silva Rocha Aguiar
