# ADR 0015 — Permissões de agentes de IA no repositório

**Status:** Aceita
**Data:** 2026-11-15
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

A equipe usa agentes de IA para escrever código, testes e documentação (ADR 0013). Esses agentes conseguem criar branches, fazer commits e abrir PRs, mas o que eles produzem nem sempre está correto, e a equipe continua responsável por tudo o que entra no repositório.

A `main` guarda a versão entregue do produto, e a `develop` reúne o trabalho integrado de cada release. Uma alteração ruim em qualquer uma das duas afeta a equipe inteira.

Desde o início do projeto, a equipe já trabalha assim: nada gerado por um agente de IA entra na `main` ou na `develop` sem que um integrante do grupo revise antes. Esta ADR registra essa prática.

## Decisão

**Nenhum agente de IA pode fazer commits diretamente na `main` ou na `develop`, nem dar merge em PRs para essas branches, sem a revisão de um integrante do grupo.**

## Consequências

- Todo código, teste ou documento gerado por IA passa por pelo menos uma pessoa da equipe antes de entrar na `main` ou na `develop`, que continua responsável pelo que aprovou.
- O merge para essas branches depende da disponibilidade de um integrante para revisar, o que pode atrasar entregas perto dos prazos.
- A regra vale para todos os agentes de IA usados pela equipe, independentemente da ferramenta.

## Alternativa considerada

**Permitir merge automático pelo agente quando o CI estiver verde.** Seria mais rápido, mas o CI não detecta tudo (por exemplo, um teste que passa sem testar nada, risco citado na ADR 0013). Descartada.

## Relacionadas

- `docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md` (uso de IA na equipe e proteção da `develop` e da `main`).
- `.github/PULL_REQUEST_TEMPLATE.md`.
