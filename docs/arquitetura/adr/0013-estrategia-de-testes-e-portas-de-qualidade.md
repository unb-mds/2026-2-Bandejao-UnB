# ADR 0013 — Estratégia de testes e portas de qualidade no CI

**Status:** Proposta
**Data:** 2026-11-06
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O RNF06 pedia cobertura mínima de **60% nos módulos críticos**, e o backlog da R2 seguia esse número (Definition of Done e BE-18). O plano de ensino de MDS 2026/2 pede outra coisa, na seção "No lugar da métrica de cobertura":

- cobertura de linhas **≥ 70%** no módulo de domínio;
- escore de mutação **≥ 50%** nos módulos críticos;
- **teste de sabotagem** em 100% dos módulos críticos;
- **0** achados críticos ou altos em aberto na análise estática (SAST).

Além disso, a nota da Release 2 só é lançada com o **CI verde no commit da entrega** e sem vulnerabilidade crítica ou alta em aberto.

O plano de ensino trata a cobertura como piso, não como prova de qualidade: um teste sem asserção aumenta a cobertura sem testar nada. Esse risco é maior no Bandejão porque a equipe usa agentes de IA para escrever código e testes (aula 23, "Testes gerados por IA e falsa confiança").

A monitoria orientou que o projeto tenha testes **unitários, de integração, de interface, de sistema, de ponta a ponta e de segurança**, mais testes específicos do tema. As aulas do Módulo 4 acrescentam **mutação, sabotagem, propriedades** e a revisão dos testes gerados por IA.

O backlog previa testes só no backend com `manage.py test`, vitest para stores e componentes no front, e um CI com lint, testes e relatório de cobertura, sem meta que barrasse o PR.

## Decisão

1. **As metas do plano de ensino passam a ser as metas do RNF06**, no backend **e** no frontend: cobertura de linhas ≥ 70% e escore de mutação ≥ 50% nos módulos críticos, sabotagem em 100% deles e 0 achados críticos ou altos em SAST e nas dependências.
2. **Todos os tipos de teste valem para as duas frentes**: unitário, integração, interface (contrato da API no back, interface gráfica no front), sistema, ponta a ponta, segurança, mutação, sabotagem, propriedades, a revisão dos testes gerados por IA e os testes específicos do tema. O detalhe está em `docs/qualidade/plano-de-testes.md`.
3. **TDD** (vermelho → verde → refatorar) é o método para os testes e para o pipeline: cada porta do CI só é aceita depois de ser vista barrando um PR de prova.
4. **As metas são portas do CI**, e não só relatórios: o job falha abaixo da meta, e a proteção da `develop` e da `main` exige todos os jobs verdes.
5. **Ferramentas:** `pytest` + `pytest-django` no back (em vez de `manage.py test`, porque o `mutmut` usa o `pytest`), `coverage.py`, `hypothesis`, `mutmut`, `bandit`, Semgrep e `pip-audit`; `vitest` com `@vitest/coverage-v8`, `@vue/test-utils`, `fast-check`, StrykerJS, Playwright, Semgrep e `npm audit` no front.
6. **Mutação incremental:** nos PRs, só os arquivos críticos alterados; a base inteira roda toda semana e antes da entrega.

## Consequências

- O RNF06 sobe de 60% para 70% e ganha três metas novas. O Documento de Requisitos (RNF06), o Documento de Visão (seção 7) e o backlog (Definition of Done, BE-01, BE-02, BE-18, FE-02 e itens novos) foram atualizados.
- O BE-02 e o FE-02 crescem (de P para M), e entram itens novos: BE-19 e FE-17 (mutação), FE-18 (ponta a ponta), FE-19 (portas finais do front), QA-10 (sabotagem) e QA-11 (auditoria dos testes gerados por IA).
- A mutação é lenta. Rodar só nos arquivos alterados mantém o PR rápido, mas um módulo crítico que ninguém altera pode perder escore sem que ninguém perceba até a rodada semanal.
- O CI passa a barrar PRs. No começo isso pode atrasar entregas, mas evita descobrir em 22/11 que a meta não foi atingida, quando já não há tempo de corrigir.
- O teste de interface do back compara o contrato gerado com o do repositório. Qualquer mudança de endpoint obriga a atualizar o contrato no mesmo PR, o que já era regra da Definition of Done.
- O ponta a ponta precisa do `docker compose` com PWA, API e banco. Ele só fica obrigatório a partir do M2, quando há fluxo completo para testar.

## Alternativas consideradas

- **Manter 60% de cobertura:** fica abaixo da meta da disciplina e não mede se os testes detectam defeito. Descartada.
- **Só cobertura, com meta mais alta (por exemplo 90%):** o próprio plano de ensino retirou essa meta, porque cobertura alta convive com testes vazios. Descartada.
- **Mutação em todo PR, na base inteira:** mede tudo sempre, mas deixa cada PR muito lento para o prazo da R2. Descartada em favor do modo incremental com rodada semanal.
- **Metas só no backend:** o front tem regras críticas (CSRF no `apiClient`, descarte das coordenadas, filtros) e entra na mesma porta de entrega. Descartada.
- **Manter `manage.py test` no back:** funciona para unitário e integração, mas o `mutmut` precisa do `pytest`. Descartada.

## Relacionadas

- Requisitos: RNF04, RNF06, RNF07, RI09, RI10.
- `docs/qualidade/plano-de-testes.md`.
- `docs/requisitos/backlog.md` (seção 1.4 e itens BE-01, BE-02, BE-18, BE-19, FE-02, FE-17 a FE-19, QA-10, QA-11).
- `docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md` (leitor como módulo crítico).
- `docs/arquitetura/adr/0008-matricula-siape-em-texto-claro.md` (teste automatizado de vazamento).
- Plano de ensino de MDS 2026/2: https://mds.lappis.rocks/planoensino/
