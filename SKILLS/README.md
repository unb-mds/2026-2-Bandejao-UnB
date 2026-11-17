# Skills do Claude — Grupo G6

Skills utilizadas pelo grupo, padronizadas nesta pasta para referência da disciplina.

## Skills disponíveis

- **estudo-semanal** — gera o relatório padronizado de estudo semanal do grupo.
- **grilling** — conduz uma sessão de perguntas para testar/aprofundar um plano ou decisão.
- **domain-modeling** — apoia a construção do modelo de domínio do projeto (terminologia, CONTEXT.md, ADRs).
- **grill-with-docs** — combina a dinâmica de perguntas com a geração de documentação (ADRs e glossário).
- **c4-architecture** — gera e atualiza os diagramas C4 (Mermaid) da pasta `docs/arquitetura/`.
- **pr-review-toolkit** — plugin de revisão de PR (`/pr-review-toolkit:review-pr`) com agentes para código, testes, tratamento de erros, comentários, tipos e simplificação. Cópia da versão 1.0.1 (17/11/2026), só para referência; para usar, instale o plugin do marketplace oficial.
- **review-status** — mostra as branches e os PRs de correção de revisão em aberto (requer o plugin review-to-pr, que não está nesta pasta).

Como, quando e em quais partes do projeto cada skill é usada: veja [`USO-DAS-SKILLS.md`](USO-DAS-SKILLS.md).

## ⚠️ Dependência entre skills

A skill **grill-with-docs** depende das skills **grilling** e **domain-modeling** para funcionar corretamente:
- de **grilling**, ela herda a dinâmica de perguntas para sondar e aprofundar o assunto;
- de **domain-modeling**, ela herda a lógica de geração/edição de ADRs e do CONTEXT.md do projeto.

Portanto, ao usar ou copiar **grill-with-docs**, é necessário manter **grilling** e **domain-modeling** também disponíveis.
