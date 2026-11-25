Como contribuir com o Bandejão
==============================

_Resumo: leia as [normas de convivência](#normas-de-convivência), prepare o ambiente com os passos de [Preparando o ambiente](#preparando-o-ambiente), crie sua branch a partir da `develop`, escreva o teste antes do código e abra um PR pequeno para a `develop`, com o CI verde e a revisão de alguém de outra frente._

Boas-vindas
-----------

O Bandejão é o PWA que reúne o cardápio, as avaliações, a previsão de fila e a gamificação dos Restaurantes Universitários (RU) da UnB. Ele foi criado pelo Grupo 6 da disciplina Métodos de Desenvolvimento de Software (MDS, FCTE/UnB, 2026/2), mas é um projeto feito pela comunidade acadêmica para a própria comunidade, e toda ajuda é bem-vinda.

Dá para contribuir de muitas formas, e nem todas envolvem escrever código:

- [relatando bugs e testando a aplicação](#testando-e-relatando-bugs);
- [organizando as issues](#ajudando-nas-issues);
- [escrevendo código](#desenvolvendo-para-o-bandejão), no backend, no frontend ou no banco;
- [revisando PRs](#revisando-código);
- [melhorando a documentação](#documentação).

A comunicação acontece principalmente pelo GitHub (issues e pull requests). Dúvidas sobre o projeto também podem ir para o e-mail da equipe, **equipe@bandejaounb.com.br**.

Antes de começar, leia estes documentos, que descrevem como o grupo trabalha:

1. As [normas de convivência](#normas-de-convivência), logo abaixo.
2. O [Documento de Visão](docs/requisitos/documento-de-visao-bandejao.md), que explica o problema que o Bandejão resolve e para quem.
3. A seção [Uso de IA nas contribuições](#uso-de-ia-nas-contribuições), que descreve as regras para quem usa assistentes de IA para escrever código, testes ou documentação.

Normas de convivência
---------------------

- **Seja respeitoso e cordial.** Critique o código, não a pessoa. Na revisão, explique o porquê e diga o que precisa mudar.
- **Pergunte.** Ninguém precisa saber tudo. Uma dúvida no PR ou na issue costuma economizar horas de retrabalho.
- **Proteja os dados de quem usa o Bandejão.** Matrícula, SIAPE e e-mail nunca aparecem em resposta pública, log, print de tela ou issue. As coordenadas do GPS não são gravadas em lugar nenhum (veja o [Aviso de privacidade](docs/requisitos/aviso-de-privacidade.md)).
- **Lembre que o Bandejão não é oficial.** Ele não é um site da UnB nem do RU. Não use a marca da UnB como se fosse oficial e não prometa informações que só o RU pode dar.
- **Conflitos** são resolvidos primeiro na conversa do próprio PR ou da issue. Se não houver acordo, o assunto vai para a reunião do grupo, e a decisão fica registrada em ata ou em ADR.

Testando e relatando bugs
-------------------------

Encontrar e relatar bugs é uma das formas mais úteis de contribuir, e não precisa da permissão de ninguém. Use o Bandejão em **https://bandejaounb.com.br**, no celular e no computador, e procure o que não funciona como o [Guia do usuário](docs/guia-do-usuario.md) descreve.

Para relatar um bug:

1. Procure nas [issues](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues) se ele já foi relatado. Se sim, comente lá com o que você viu de diferente.
2. Se não, abra uma issue com o template **🐛 Bug**, informando:
   - o que aconteceu;
   - o passo a passo para reproduzir;
   - o comportamento esperado;
   - a área afetada (Frontend, Backend, Banco de Dados ou Infra/PWA);
   - o navegador e o aparelho usados.
3. Não coloque no print nem no texto seu e-mail, sua matrícula ou sua localização.

Também ajuda muito escrever **testes** para bugs que outras pessoas relataram, ou para partes do código com pouca cobertura. Veja como no [Plano de testes](docs/qualidade/plano-de-testes.md).

Ajudando nas issues
-------------------

Organizar as issues ajuda a equipe a saber o que fazer primeiro. Você pode:

1. tentar reproduzir um bug relatado e comentar se conseguiu, em qual navegador e aparelho;
2. pedir mais detalhes quando o relato não basta para reproduzir o problema;
3. apontar issues duplicadas, com o link da original;
4. conferir se a issue usa o template certo (**📋 História de Usuário**, **🔧 Tarefa** ou **🐛 Bug**) e o ID do [Backlog do produto](docs/requisitos/backlog.md) (`BD-`, `BE-`, `FE-`, `QA-`, `DOC-`).

Desenvolvendo para o Bandejão
-----------------------------

Se você prefere escrever código, escolha uma issue aberta no [repositório](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues) ou um item ainda não feito do [Backlog do produto](docs/requisitos/backlog.md). Comente na issue que vai trabalhar nela, para ninguém fazer o mesmo trabalho em paralelo.

Para contribuir com código, você vai precisar conhecer os processos e as convenções do grupo. Os documentos abaixo estão **em ordem**, e recomendamos lê-los nessa sequência:

1. **[Preparando o ambiente](#preparando-o-ambiente)**, nesta página: como rodar o backend e o frontend na sua máquina.
2. **[Glossário do domínio](docs/requisitos/CONTEXT-DOMINIO.md)**: os termos do projeto (Campus, Refeição, Marcador, Check-in, Patente…). O código e os textos usam esses nomes. Por exemplo, *Marcador*, e não "alérgeno".
3. **[Arquitetura (C4)](docs/arquitetura/c4-niveis-1-2.md)**: níveis 1 e 2 e, depois, o nível 3 e o nível 4 da parte em que você vai mexer ([backend](docs/arquitetura/backend/c4-nivel-3-backend.md), [frontend](docs/arquitetura/front-end/c4-niveis-3-4-frontend-bandejao.md) ou [banco](docs/arquitetura/banco-de-dados/C4-nivel-3-banco-de-dados-bandejao.md)). Classes, tabelas, componentes e stores têm os mesmos nomes do C4.
4. **[Documento de Requisitos](docs/requisitos/documento-de-requisitos-bandejao.md)**: os critérios Dado/Quando/Então de cada requisito, as regras de negócio (Anexo B) e os parâmetros configuráveis (Anexo A).
5. **[Plano de testes](docs/qualidade/plano-de-testes.md)** e **[ADR 0013](docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md)**: TDD, tipos de teste e portas de qualidade do CI.
6. **[Fluxo de trabalho](#fluxo-de-trabalho)**, nesta página: branches, commits, pull requests e Definition of Done.
7. **[Decisões de arquitetura (ADRs)](docs/arquitetura/adr/)**: antes de propor uma mudança grande, veja se ela já foi discutida. Para uma decisão nova, escreva uma ADR antes de programar.

### Preparando o ambiente

**Pré-requisitos:** Git, Python 3.14, Node `^22.18.0` ou `>=24.12.0` e, para os testes de ponta a ponta, Docker.

Clone o repositório:

```bash
git clone https://github.com/unb-mds/2026-2-Bandejao-UnB.git
cd 2026-2-Bandejao-UnB
git switch develop
```

#### Backend (Django + DRF)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # em desenvolvimento, os valores padrão funcionam
python manage.py migrate
python manage.py loaddata campi marcadores
python manage.py runserver         # API em http://localhost:8000/api/
```

- Em desenvolvimento, o banco é SQLite (`db.sqlite3`). Para testar com MySQL, defina `DB_ENGINE=mysql` e as variáveis `DB_*` do `.env.example`.
- Com `DJANGO_DEBUG=True`, os e-mails (confirmação de cadastro, por exemplo) aparecem no terminal do `runserver`, e não é preciso configurar o Brevo.
- Para carregar o cardápio da semana a partir da página do RU: `python manage.py ler_cardapio`.

Os mesmos comandos do CI, para conferir antes do PR:

```bash
ruff check . && ruff format --check .
pytest --cov=apps --cov-branch --cov-fail-under=70
bandit -r apps config -lll
pip-audit -r requirements-dev.txt
python manage.py makemigrations --check --dry-run
```

#### Frontend (Vue 3 + Vite)

```bash
cd frontend
npm install
npm run dev                        # PWA em http://localhost:5173
```

Por padrão, o `npm run dev` usa um **backend simulado** (`src/services/mock/`), que não precisa do Django. A conta de demonstração está no [README do frontend](frontend/README.md). Para usar a API real, suba o Django em `localhost:8000` e crie `frontend/.env.local` com:

```bash
VITE_USE_MOCK=false
```

Os mesmos comandos do CI:

```bash
npm run lint:ci
npm run test:ci
npm run build
npm audit --audit-level=high
```

Os testes de ponta a ponta (Playwright), a mutação (StrykerJS) e os detalhes de cada job do CI estão no [README do frontend](frontend/README.md).

#### Documentação (Docsify)

```bash
python -m http.server 3000 --directory docs   # na raiz do repositório
```

Abra http://localhost:3000. Uma página nova precisa de um link em [`docs/_sidebar.md`](docs/_sidebar.md).

### Fluxo de trabalho

**Branches (Gitflow).** O trabalho do dia a dia acontece na `develop`, e a `main` recebe as entregas e vai para produção sozinha, pelo deploy contínuo. Crie sua branch a partir da `develop`:

```bash
git switch develop && git pull
git switch -c feature/<issue>-<id>-<descricao-curta>
```

Use o prefixo de acordo com o tipo: `feature/…`, `fix/…`, `docs/…` ou `chore/…`. Ninguém, pessoa ou agente de IA, faz commit nem push direto na `develop` ou na `main`: tudo entra por PR ([ADR 0015](docs/arquitetura/adr/0015-permissoes-de-agentes-de-ia-no-repositorio.md)).

**Antes de programar (SDD).** Preencha a issue com os critérios de aceite e, se houver endpoint, o contrato (método, entrada, saída e erros), antes de escrever o código.

**TDD.** O teste entra num commit **antes** do código: vermelho → verde → refatorar. Quem revisa confere essa ordem no histórico do PR.

**Commits.** Use *Conventional Commits*, em português, com o escopo e a issue:

```
test(front): legenda dos níveis da previsão da fila (FE-23, #291)
fix(front): legenda dos níveis no gráfico da fila do desktop (FE-23, #291)
docs: C4 do front e checklist de qualidade com o desktop da FE-23 (#291)
```

Os tipos mais usados são `feat`, `fix`, `test`, `refactor`, `docs` e `chore`. Os ajustes pedidos na revisão viram commits próprios, como `docs: ajustes da revisão da FE-23 no AI-USAGE (#291)`.

**Pull request.**

1. Abra o PR **para a `develop`**, pequeno e focado num item só.
2. Preencha o [template de PR](.github/PULL_REQUEST_TEMPLATE.md): descrição, `Closes #<issue>`, tipo de mudança, checklist, como testar e, se a mudança for visual, prints.
3. Se um endpoint mudou, atualize o [`backend/openapi.yaml`](backend/openapi.yaml) no mesmo PR.
4. Se a implementação divergir do C4, atualize o documento de arquitetura no mesmo PR.
5. Dependência nova leva o link do pacote oficial na descrição do PR.
6. Se usou IA, registre a entrada do PR no [`AI-USAGE.md`](AI-USAGE.md) (veja [Uso de IA nas contribuições](#uso-de-ia-nas-contribuições)).

**CI.** Todo PR roda o GitHub Actions. O merge só acontece com tudo verde:

| Onde | O que reprova |
|---|---|
| Backend | Ruff (lint e formatação); teste falhando; cobertura abaixo de 70%; Bandit, pip-audit ou Semgrep com achado alto ou crítico; testes no MySQL 8.4; migration pendente; mutação abaixo de 50% nos arquivos críticos alterados |
| Ponta a ponta | Fluxo quebrado nos testes do Playwright (celular e desktop), que sobem o PWA, a API e o MySQL. Roda em todo PR, qualquer que seja a base |
| Frontend | Erro ou aviso do Oxlint/ESLint; teste falhando; cobertura abaixo de 70% nos arquivos críticos; erro no build; `npm audit` ou Semgrep com achado alto ou crítico; mutação abaixo de 50% nos arquivos críticos alterados |

**Definition of Done.** O PR só entra quando cumpre a [Definition of Done](docs/requisitos/backlog.md) do backlog. Os pontos que mais aparecem na revisão:

- [ ] teste antes do código, no histórico do PR;
- [ ] testes no mesmo PR, no back e no front, conforme o Plano de testes;
- [ ] CI verde;
- [ ] contrato OpenAPI atualizado, se um endpoint mudou;
- [ ] nada de matrícula, SIAPE ou e-mail em resposta pública ou log, e nenhuma coordenada gravada;
- [ ] valores do Anexo A lidos da configuração, nunca fixos no código;
- [ ] nomes iguais aos da arquitetura e do glossário;
- [ ] revisão de alguém de **outra frente**.

**Merge.** O merge é feito por um integrante, depois da revisão de alguém diferente de quem escreveu o código (ou de quem operou o agente de IA). Todo merge na `develop` atualiza o site da documentação, e todo merge na `main` vai para produção.

### Ajudando com PRs que já existem

Se você já conhece o processo e não sabe o que fazer em seguida, ajude a terminar um PR parado: veja os [PRs abertos](https://github.com/unb-mds/2026-2-Bandejao-UnB/pulls), pergunte ao autor o que falta e ofereça ajuda com os testes, a documentação ou os ajustes da revisão.

Revisando código
----------------

Revisar código vale tanto quanto escrever. É um dos jeitos mais rápidos de conhecer o projeto e ajuda a equipe a andar mais rápido. Ninguém fica com PR parado mais de um dia.

Para revisar um PR:

1. **Confira a Definition of Done** e o checklist do template.
2. **Olhe o histórico de commits:** o `test(...)` vem antes do `feat`/`fix`?
3. **Rode localmente**, seguindo o "Como testar" do PR.
4. **Confira os testes:** se foram gerados por IA, passe pelo checklist do [Plano de testes (3.10)](docs/qualidade/plano-de-testes.md) e faça uma sabotagem rápida em pelo menos um teste (quebre o código e veja se o teste falha).
5. **Confira os nomes** com o C4 e o glossário.
6. **Seja cordial:** explique o porquê e diga o que precisa mudar para o PR ser aprovado.

O plugin `pr-review-toolkit` ajuda a revisar antes de abrir o PR e a revisar o PR de um colega, mas **não substitui a revisão humana** (veja as [skills do projeto](SKILLS/USO-DAS-SKILLS.md)).

Documentação
------------

A documentação fica em [`docs/`](docs/) e é publicada no **GitHub Pages** (Docsify) a cada merge na `develop`: **https://unb-mds.github.io/2026-2-Bandejao-UnB/**

- Página nova: crie o `.md` em `docs/` e adicione o link em [`docs/_sidebar.md`](docs/_sidebar.md).
- Diagramas: use blocos ` ```mermaid `. Os diagramas C4 seguem a skill `c4-architecture`.
- Decisão de arquitetura: registre como nova ADR em `docs/arquitetura/adr/`, com o próximo número, e adicione ao menu.
- Estudo da semana: o resumo vai em `docs/estudos/semanaXX-assunto.md`.
- Mudou o que a pessoa usuária vê? Atualize o [Guia do usuário](docs/guia-do-usuario.md) no mesmo PR.

Um jeito muito produtivo de melhorar a documentação é usar o Bandejão ou o código e parar sempre que tiver uma dúvida: encontre a resposta e escreva-a no lugar onde você procurou primeiro.

Uso de IA nas contribuições
---------------------------

A equipe usa assistentes de IA para escrever código, testes e documentação. As regras valem para o comportamento de quem contribui, e não para a ferramenta: o problema não é usar IA, é entregar o que não se entende ou não se conferiu.

1. **Você é responsável pelo que envia.** Revise todo código, teste e texto gerado por IA antes de abrir o PR e antes de pedir uma nova revisão. Você precisa conseguir explicar cada linha.
2. **Agentes não fazem commit, push nem merge na `develop` ou na `main`.** Nas branches de trabalho, podem commitar e fazer push. O merge é de um integrante, depois da revisão de outra pessoa ([ADR 0015](docs/arquitetura/adr/0015-permissoes-de-agentes-de-ia-no-repositorio.md)).
3. **Confira os testes gerados por IA** com o checklist do Plano de testes (3.10). Testes vazios, que só repetem a implementação ou que simulam a própria unidade não contam.
4. **Não invente dependências.** Pacote novo leva o link do repositório oficial no PR.
5. **Responda a revisão de verdade.** Se o revisor pediu uma mudança, confira que ela está no código antes de dizer que está feita.
6. **Edite o texto gerado.** Descrições de PR, issues e comentários gerados por IA costumam ser longos demais. Deixe só o que importa.
7. **Registre o uso** no [`AI-USAGE.md`](AI-USAGE.md), com: PR, ferramenta, apoio recebido, TDD, validação, revisão humana e situação. Toda skill usada entra no campo **Ferramenta** ou **Apoio**.

As skills de IA que o grupo usa, e quando usar cada uma, estão em [`SKILLS/USO-DAS-SKILLS.md`](SKILLS/USO-DAS-SKILLS.md).

Releases e produção
-------------------

A `main` recebe as entregas de cada release, e todo merge nela vai para produção pelo deploy contínuo, depois que o CI passa. Quem for mexer na infraestrutura (Docker Compose, Caddy, tarefas periódicas, banco de produção) deve ler antes o guia de [Deploy de produção](docs/deploy/deploy-producao.md) e combinar com a equipe: a produção tem contas reais, e toda migration exige backup antes.
