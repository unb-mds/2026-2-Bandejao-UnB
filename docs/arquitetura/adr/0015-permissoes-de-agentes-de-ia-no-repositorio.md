# ADR 0015 — Permissões de agentes de IA no repositório

**Status:** Aceita (proposta em 2026-11-18, aceita em 2026-11-19 na revisão do PR #156)
**Data:** 2026-11-18 (redigida em 2026-11-15)
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

A equipe usa agentes de IA para escrever código, testes e documentação (ADR 0013). Esses agentes conseguem criar branches, fazer commits e abrir PRs, mas o que eles produzem nem sempre está correto, e a equipe continua responsável por tudo o que entra no repositório.

A `develop` reúne o trabalho integrado de cada release, e a `main` recebe as entregas de cada release. Uma alteração ruim em qualquer uma das duas afeta a equipe inteira.

A Definition of Done (`docs/requisitos/backlog.md` §1.4) já prevê revisão antes do merge nos PRs para a `develop`, por alguém de outra frente. Esta ADR deixa a regra explícita para o trabalho feito com agentes de IA: estende a revisão à `main` e fixa o mínimo para esse trabalho, sem dispensar a DoD.

## Decisão

**Agentes de IA não fazem commit nem push direto na `main` ou na `develop`; toda mudança entra por PR. Agentes não fazem merge desses PRs: o merge é feito por um integrante, depois da revisão de alguém diferente de quem operou o agente.**

- "Push direto" inclui force-push. Agentes também não apagam nem renomeiam a `main` ou a `develop`.
- A regra vale para a `main` e a `develop`. Nas branches de trabalho (`feature/…`, `fix/…`, `docs/…` e `chore/…`, README), o agente pode commitar e fazer push.
- Por enquanto, a regra é um acordo da equipe. A `main` e a `develop` estão protegidas com as mesmas regras (a `main` desde 2026-11-19, configurada durante a revisão do PR #156): toda mudança entra por PR, os jobs `lint`, `testes`, `seguranca` e `testes-mysql` precisam estar verdes e a branch atualizada, e force-push e exclusão estão bloqueados. A proteção exige 0 aprovações e não vale para administradores. Além disso, o agente usa a conta do integrante que o opera, então o GitHub não distingue os dois.

## Consequências

- Toda mudança feita com agente de IA passa por pelo menos um integrante diferente de quem operou o agente, que continua responsável pelo que aprovou, antes de entrar na `main` ou na `develop`.
- O merge para essas branches depende da disponibilidade de outro integrante para revisar, o que pode atrasar entregas perto dos prazos.
- A regra vale para todos os agentes de IA usados pela equipe, independentemente da ferramenta.
- A proteção impede, para quem não é administrador, commit direto, force-push e exclusão da `main` e da `develop`. Ela não exige a revisão de outro integrante nem vale para administradores, e um agente operado pela conta de um administrador consegue fazer tudo isso; essas partes dependem da equipe.

## Alternativa considerada

**Permitir merge automático pelo agente quando o CI estiver verde.** Seria mais rápido, mas o CI não pega tudo: a mutação, quando entrar no CI, vai rodar só nos arquivos críticos alterados (ADR 0013, decisão 6), e erros de regra de negócio ou dependências inventadas só aparecem na revisão humana (ADR 0013; Plano de Testes 3.10). Descartada.

## Pontos em aberto

- Se a proteção da `main` e da `develop` vai passar a exigir pelo menos uma aprovação ("Require approvals") e valer também para administradores, ou se a revisão por outro integrante fica como acordo da equipe.

## Relacionadas

- `docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md` (uso de IA na equipe e proteção da `develop` e da `main`).
- `docs/requisitos/backlog.md` §1.4 (Definition of Done: revisão por alguém de outra frente).
- `docs/qualidade/plano-de-testes.md` §3.10 (checklist do revisor para testes gerados por IA).
- `AI-USAGE.md` (registro do uso de IA em cada PR, com o campo "Revisão humana").
