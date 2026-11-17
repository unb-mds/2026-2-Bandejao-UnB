# Uso das skills no projeto

Este documento registra **como**, **quando** e **em quais partes do projeto** o grupo G6 usa cada skill do Claude guardada nesta pasta. Ele complementa o [`README.md`](README.md), que lista as skills disponíveis, e o [`AI-USAGE.md`](../AI-USAGE.md), que registra o uso de IA em cada PR.

## Resumo

| Skill | Quando usar | Partes do projeto |
|---|---|---|
| [estudo-semanal](#estudo-semanal) | Depois de estudar um assunto, antes de commitar o relatório | `docs/estudos/` |
| [grilling](#grilling) | Para testar um plano ou uma decisão antes de implementar | Planejamento de itens do `docs/requisitos/backlog.md` e decisões de arquitetura |
| [domain-modeling](#domain-modeling) | Ao discutir termos do domínio ou registrar uma decisão | `CONTEXT.md` e `docs/arquitetura/adr/` |
| [grill-with-docs](#grill-with-docs) | Quando a conversa sobre o plano deve virar ADR e glossário | `CONTEXT.md` e `docs/arquitetura/adr/` |
| [c4-architecture](#c4-architecture) | Ao criar ou atualizar diagramas C4 | `docs/arquitetura/` (níveis 1 a 4 do back, do front e do banco) |
| [pr-review-toolkit](#pr-review-toolkit) | Antes de abrir um PR e ao revisar o PR de um colega | `backend/`, `frontend/`, testes e documentação alterados no PR |
| [review-status](#review-status) | Para ver as branches e os PRs de correção em aberto | Branches de correção e PRs no GitHub |

## Fluxo de trabalho

As skills acompanham as etapas de um item do backlog:

1. **Estudo:** `estudo-semanal` gera o relatório do assunto estudado.
2. **Planejamento:** `grilling` testa o plano. Quando o plano gera decisões ou termos novos, `grill-with-docs` (com `domain-modeling`) registra a ADR e atualiza o `CONTEXT.md`.
3. **Arquitetura:** `c4-architecture` cria ou atualiza o diagrama C4 do nível afetado.
4. **Implementação:** segue o TDD do Plano de Testes. Nenhuma skill substitui o commit `test(...)` antes do `feat`/`fix`.
5. **Revisão:** `pr-review-toolkit` revisa o código antes do PR e apoia a revisão do colega. `review-status` mostra o que ainda está aberto.
6. **Registro:** o uso de IA, incluindo as skills, entra no `AI-USAGE.md` do PR.

## Detalhes de cada skill

### estudo-semanal

- **O que faz:** gera o relatório padronizado de estudo semanal, com resumo do assunto e aplicação no projeto.
- **Quando:** depois que um integrante estuda um assunto da semana e antes do commit do relatório. Também serve para corrigir a formatação de um relatório já escrito.
- **Onde:** relatórios em `docs/estudos/` (por exemplo, `semana03-c4-model.md`).
- **Como:** peça "gerar o relatório do meu estudo da semana sobre X". Confira se o nome do arquivo segue o padrão usado em `docs/estudos/`. A skill sugere `estudos/semana-XX/`, mas o repositório usa `docs/estudos/semanaXX-assunto.md`.

### grilling

- **O que faz:** faz perguntas seguidas sobre um plano ou uma decisão até que fique claro, montando uma árvore de decisões.
- **Quando:** antes de começar um item do backlog com regra de negócio nova ou de tomar uma decisão de arquitetura.
- **Onde:** planejamento dos itens de `docs/requisitos/backlog.md` e decisões que depois viram ADRs.
- **Como:** "me faça um grill sobre o plano do item X". O resultado é a conversa, não um arquivo. Para registrar o resultado, use `grill-with-docs`.

### domain-modeling

- **O que faz:** mantém o modelo de domínio do projeto (termos e relações) e registra decisões em ADRs.
- **Quando:** quando surge ou muda um termo do domínio (Campus, RU, Cardápio, Fila…) ou quando uma decisão precisa de ADR.
- **Onde:** [`CONTEXT.md`](../CONTEXT.md) (glossário) e [`docs/arquitetura/adr/`](../docs/arquitetura/adr/) (ADRs 0001 a 0014).
- **Como:** use os termos do `CONTEXT.md` nos nomes do código e nos diagramas C4 nível 4. Uma ADR nova segue a numeração da pasta.

### grill-with-docs

- **O que faz:** junta as perguntas do `grilling` com o registro de ADRs e do glossário do `domain-modeling`.
- **Quando:** em decisões de projeto que precisam ser discutidas e registradas, por exemplo hospedagem, sessão, regras de gamificação.
- **Onde:** `CONTEXT.md` e `docs/arquitetura/adr/`.
- **Como:** só funciona com `grilling` e `domain-modeling` disponíveis (veja o `README.md`). Ela não é chamada automaticamente (`disable-model-invocation`), então peça pelo nome: `/grill-with-docs`.

### c4-architecture

- **O que faz:** gera diagramas C4 em Mermaid (contexto, contêineres, componentes, implantação e fluxos) com boas práticas e erros comuns a evitar.
- **Quando:** ao criar ou atualizar a arquitetura: um módulo novo, uma mudança de contêiner ou de infraestrutura, ou um nome de classe que muda no nível 4.
- **Onde:**
  - Níveis 1 e 2: [`docs/arquitetura/c4-niveis-1-2.md`](../docs/arquitetura/c4-niveis-1-2.md)
  - Back-end: [`docs/arquitetura/backend/`](../docs/arquitetura/backend/) (nível 3 e os níveis 4 de avaliação, cadastro e autenticação, exposição do cardápio, fila, gamificação e leitor do cardápio)
  - Front-end: [`docs/arquitetura/front-end/`](../docs/arquitetura/front-end/)
  - Banco de dados: [`docs/arquitetura/banco-de-dados/`](../docs/arquitetura/banco-de-dados/)
- **Como:** peça "atualize o C4 nível 4 de X". A skill grava por padrão em `docs/architecture/` com nomes em inglês. No nosso repositório, diga para usar `docs/arquitetura/` e os arquivos que já existem. Os nomes no nível 4 precisam bater com o código, e `backend/tests/test_estrutura.py` confere a estrutura do nível 3.

### pr-review-toolkit

- **O que faz:** plugin oficial da Anthropic com o comando `/pr-review-toolkit:review-pr` e seis agentes de revisão:
  - `code-reviewer`: qualidade geral e convenções do projeto
  - `pr-test-analyzer`: cobertura e qualidade dos testes
  - `silent-failure-hunter`: erros engolidos e falhas silenciosas
  - `comment-analyzer`: comentários e docstrings que não batem com o código
  - `type-design-analyzer`: design de tipos e invariantes
  - `code-simplifier`: simplifica o código sem mudar o comportamento
- **Quando:** antes de abrir um PR (sobre o `git diff` da branch) e ao revisar o PR de um colega. Também depois dos ajustes da revisão, antes do recheck.
- **Onde:** código do `backend/` (Django/DRF) e do `frontend/` (Vue 3), testes, `openapi.yaml` e documentação alterados no PR.
- **Como:** rode `/pr-review-toolkit:review-pr` na branch do PR. Para focar em uma parte, passe o aspecto: `tests`, `errors`, `comments`, `types`, `code` ou `simplify`. A revisão por IA **não substitui a revisão humana** exigida no DoD. Os achados aceitos viram commits `tipo(escopo): ajustes da revisão … (#N)` e o uso é registrado no `AI-USAGE.md`.
- **Instalação:** os arquivos estão em `pr-review-toolkit/` só para referência. Para usar, instale o plugin `pr-review-toolkit` do marketplace oficial (`claude-plugins-official`) no Claude Code.

### review-status

- **O que faz:** mostra as branches e os PRs de correção abertos e limpa as worktrees de PRs já fechados.
- **Quando:** para saber quais correções de revisão ainda estão pendentes.
- **Onde:** branches de correção e PRs do repositório no GitHub.
- **Como:** `/review-status`. Ela depende do script `lib/autofix.sh` do plugin review-to-pr, que não está nesta pasta. Sem esse plugin, a skill não roda.

## Observações

- Para uma skill funcionar, o arquivo precisa se chamar `SKILL.md` dentro da pasta da skill. Ao adicionar uma skill nova nesta pasta, mantenha esse nome.
- Toda skill usada em um PR deve aparecer na entrada do PR no `AI-USAGE.md`, no campo **Ferramenta** ou **Apoio**.
