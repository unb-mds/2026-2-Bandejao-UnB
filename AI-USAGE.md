# Uso de IA

Cada entrada deve informar a tarefa/PR, a ferramenta utilizada, o apoio recebido, as evidências de validação e a situação da revisão humana. Os resultados detalhados dos testes ficam no PR e nas execuções do CI.

## BD-02 — CI com MySQL 8.4

- PR: [#124 — CI com MySQL 8.4](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/124).
- Ferramenta: ChatGPT.
- Apoio: elaboração e revisão dos testes, configuração explícita do isolamento no Django, configuração do banco de testes, job MySQL no GitHub Actions, atualização da documentação e orientação para tratar os comentários do review.
- TDD: testes adicionados no commit `d251466`, antes da implementação; falha inicial registrada pela ausência de isolamento explícito.
- Validação inicial: resultados de SQLite, MySQL e cobertura registrados na descrição do PR e na [execução verde do CI](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/43680330500).
- Prova com migration: `cardapio.0002_prova_bd02` aplicada com sucesso no MySQL no [PR #125](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/125), fechado sem merge.
- Proteção da branch: job `testes-mysql` configurado como obrigatório na `develop`.
- Validação dos ajustes do review: [CI aprovado no commit 62f0e67](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/43730856149).
- Revisão humana: [revisão dos ajustes por AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/124#pullrequestreview-5911855469), com merge autorizado após as correções finais.
- Situação: observações finais registradas neste ajuste; conferir os checks do último commit antes do merge.

## BD-04 — Parâmetros do Anexo A

- Issue: #90.
- Branch: `feature/bd-04-parametros-anexo-a`; PR ainda não aberto.
- Ferramenta: ChatGPT.
- Apoio: consulta da issue, requisitos e arquitetura; elaboração de testes e configurações; refatoração dos consumidores de cadastro; atualização da documentação e orientação pelo CMD.
- TDD: testes executados e registrados em commits antes das respectivas implementações. Exemplos: fuso (`9a9b151` → `0339bb8`), horários (`293121a` → `1c9e19d`), login (`b1858d7` → `368e61f`) e confirmação/exclusão de pendentes (`608dc1c` → `20e8b9b`).
- Validação local: suíte completa em SQLite com 793 testes aprovados e 1 ignorado, específico de MySQL. Testes de configuração e consumo verificaram também valores temporariamente alterados.
- Parâmetros pendentes: datas de término dos semestres sem entradas; precisão mínima e idade máxima da posição sem valores definidos. Nenhum valor foi inventado.
- Limites: configurações disponibilizadas para consumidores futuros não implementam endpoints, tarefas agendadas ou integração com o front-end.
- CI e MySQL: validação desta branch ainda pendente.
- Revisão humana: pendente revisão por outra frente, incluindo o checklist de testes gerados por IA do Plano de Testes.
