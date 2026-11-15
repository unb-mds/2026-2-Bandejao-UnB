# Uso de IA

## BD-02 — CI com MySQL

- Ferramenta: ChatGPT.
- Apoio: elaboração dos testes, configuração do Django, job MySQL no GitHub Actions e orientação para validação do CI.
- TDD: testes adicionados no commit `d251466`, antes da implementação; falha inicial registrada pela ausência de isolamento explícito.
- Validação local em SQLite: 561 testes passaram, 1 ignorado; cobertura de 97,37%.
- Validação no CI em SQLite: 561 testes passaram, 1 ignorado; cobertura de 97,37%.
- Validação no CI em MySQL 8.4: 562 testes passaram; cobertura de 97,37%, com verificação de `utf8mb4` e `READ COMMITTED`.
- Prova com migration: `cardapio.0002_prova_bd02` aplicada com sucesso no MySQL no [PR #125](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/125).
- Evidência: [execução do CI com os quatro jobs verdes](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/43680330500).
- Proteção da branch: job `testes-mysql` configurado como obrigatório na `develop`.
- Revisão dos testes por alguém de outra frente, incluindo o checklist do Plano de Testes: pendente.