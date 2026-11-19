# ADR 0015 — Permissões de agentes de IA no repositório

**Status:** Proposta
**Data:** 2026-11-18 (redigida em 2026-11-15)
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

A equipe usa agentes de IA para escrever código, testes e documentação (ADR 0013). Esses agentes conseguem criar branches, fazer commits e abrir PRs, mas o que eles produzem nem sempre está correto, e a equipe continua responsável por tudo o que entra no repositório.

A `develop` reúne o trabalho integrado de cada release, e a `main` recebe as entregas de cada release. Uma alteração ruim em qualquer uma das duas afeta a equipe inteira.

A Definition of Done (`docs/requisitos/backlog.md` §1.4) já prevê revisão antes do merge; esta ADR deixa a regra explícita para o trabalho feito com agentes de IA.

## Decisão

**Agentes de IA não fazem commit nem push direto na `main` ou na `develop`; toda mudança entra por PR. Agentes não fazem merge desses PRs: o merge é feito por um integrante, depois da revisão de alguém diferente de quem operou o agente.**

- "Push direto" inclui force-push. Agentes também não apagam nem renomeiam a `main` ou a `develop`.
- A regra vale para a `main` e a `develop`. Nas branches de trabalho (`feature/…`, `fix/…`, `docs/…` e `chore/…`, README), o agente pode commitar e fazer push.
- Por enquanto, a regra é um acordo da equipe. A proteção das branches exige só os jobs do CI verdes (ADR 0013), e o agente usa a conta do integrante que o opera, então o GitHub não distingue os dois.

## Consequências

- Toda mudança feita com agente de IA passa por pelo menos um integrante diferente de quem operou o agente, que continua responsável pelo que aprovou, antes de entrar na `main` ou na `develop`.
- O merge para essas branches depende da disponibilidade de outro integrante para revisar, o que pode atrasar entregas perto dos prazos.
- A regra vale para todos os agentes de IA usados pela equipe, independentemente da ferramenta.
- Enquanto a regra não estiver na proteção das branches, nada impede tecnicamente que ela seja quebrada; o cumprimento depende da equipe.

## Alternativa considerada

**Permitir merge automático pelo agente quando o CI estiver verde.** Seria mais rápido, mas o CI não pega tudo: a mutação só roda nos arquivos críticos alterados, e erros de regra de negócio, de documentação ou dependências inventadas só aparecem na revisão humana (ADR 0013; Plano de Testes 3.10). Descartada.

## Pontos em aberto

- Se a regra vai virar "Require approvals" na proteção da `main` e da `develop`, ou se fica como acordo da equipe.

## Relacionadas

- `docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md` (uso de IA na equipe e proteção da `develop` e da `main`).
- `docs/requisitos/backlog.md` §1.4 (Definition of Done: revisão por alguém de outra frente).
- `docs/qualidade/plano-de-testes.md` §3.10 (checklist do revisor para testes gerados por IA).
- `AI-USAGE.md` (registro do uso de IA em cada PR, com o campo "Revisão humana").
