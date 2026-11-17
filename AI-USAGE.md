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

## BD-03 — Fixtures e inicialização da pontuação

- PR: [#129 — Fixtures e inicialização da pontuação](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/129).
- Ferramenta: ChatGPT.
- Apoio: elaboração dos testes, fixtures de campi e marcadores, data migration de inicialização da pontuação, campo de disponibilidade da confirmação e atualização da documentação.
- TDD: etapas vermelhas registradas pela ausência das fixtures, da data migration e do campo `confirmacao_ativa`, antes das respectivas implementações.
- Validação específica após o review em SQLite: 16 testes do BD-03 aprovados, além de 7 testes de estrutura e sincronização dos models.
- TDD dos ajustes: 8 testes falharam por ausência de `IntegrityError` antes das constraints; após a implementação, os 11 testes de disponibilidade e invariantes dos raios passaram.
- Dados dos campi: coordenadas aproximadas fornecidas pela equipe a partir de mapas, arredondadas para seis casas decimais e ainda sem validação em campo.
- Raios provisórios: 150 m para Darcy Ribeiro, Ceilândia, Gama e Planaltina, definidos pela equipe e sujeitos à validação do BD-06.
- Fazenda Água Limpa: a coordenada disponível representa a fazenda, não o RU. A fixture registra `confirmacao_ativa = false` e os dois raios iguais a zero, indicando indisponibilidade.
- Detecção de campus: os campos `centro_*` e `raio_deteccao_metros` repetem provisoriamente os valores cadastrados para confirmação, até a definição dos parâmetros no BD-E3.
- Integração com a BE-09: o serviço de confirmação deverá verificar `confirmacao_ativa` antes de calcular a distância e recusar a confirmação quando o campo for falso. O BD-03 registra essa configuração e não implementa o endpoint de check-in.
- Evidências: histórico de commits, descrição e execuções do CI vinculadas ao PR #129.
- Validação completa local anterior aos ajustes do review, em SQLite: 747 testes passaram, 1 foi ignorado por ser específico de MySQL; cobertura de 97,62%.
- Validação completa local após os ajustes do review, em SQLite: 807 testes aprovados, 1 ignorado por ser específico de MySQL; cobertura de 97,67%.
- Validação no CI do commit `e8f3c87`: SQLite com 807 testes aprovados e 1 ignorado; MySQL 8.4 com 808 testes aprovados; cobertura de 97,67% nos dois bancos. Os quatro jobs foram aprovados.
- Evidência da validação: [execução verde dos ajustes do review](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/43990867511).
- Revisão humana: [segunda revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/129#issuecomment-6937610684), com os ajustes obrigatórios conferidos e merge aprovado; [aprovação formal](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/129#pullrequestreview-5932481529).
- Situação: aprovado para merge na segunda revisão. As sugestões remanescentes são opcionais; conferir os checks do último commit antes do merge.

## BE-08 — Lista de campi (`GET /api/campi/`)

- PR: [#128 — BE-08: lista de campi](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/128).
- Ferramenta: Claude (Anthropic).
- Apoio: implementação a partir do guia da BE-08 (testes, `LocalizacaoCampusConfig`, `CampiView` com `ETag` e 304, `openapi.yaml` e nota do C4 N4 4b), redação dos comentários nas issues #89 e #101 e ajustes pedidos na revisão (412 do `get_conditional_response`, `ETag` sobre os bytes do corpo, testes de usuário logado, 405 e listas no `If-None-Match`, log da tabela vazia e textos da documentação).
- TDD: testes no commit 2d39d31, antes da implementação (bfc4b95); nos ajustes da revisão, testes no commit b533e5d, que falhou com o 412, o corpo com indent e a falta do log, antes da correção (08dd145).
- Validação: `pytest` com 779 testes passando e cobertura de 97,68%, `ruff`, `bandit`, `makemigrations --check` e `spectacular --validate --fail-on-warn` rodados localmente; resultado do CI (incluindo `testes-mysql`) no PR.
- Revisão humana: [revisão e recheck por AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/128#pullrequestreview-5924918697), com merge autorizado após os ajustes.
- Situação: mergeado na `develop`.

## #110 — `makemigrations --check` no CI do backend

- PR: [#131 — makemigrations --check no CI do backend](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/131).
- Ferramenta: Claude (Anthropic).
- Apoio: teste `test_models_e_migrations_estao_sincronizados` em `backend/tests/test_estrutura.py`, nota no plano de testes (seção 5.1) e PR de prova.
- TDD: o teste já passa na `develop` ("No changes detected"); a falha foi comprovada localmente mudando `Campus.nome` sem migration e no [PR de prova #130](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/130), fechado sem merge ([execução vermelha](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/43929798081): `testes` no teste novo e `testes-mysql` em "Conferir migrations pendentes").
- Validação: `pytest` com 780 testes passando e cobertura de 97,67%, `ruff` e `makemigrations --check` rodados localmente; resultado do CI no PR.
- Revisão humana: [revisão de Poviovsky](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/131#pullrequestreview-5925503890), aprovada com uma sugestão (falha sem o traceback do Django, com `pytrace=False`) e observações (duplicação intencional no `testes-mysql` e entrada da BE-08), aplicadas nos ajustes da revisão.
- Situação: ajustes da revisão aplicados; pronto para o merge.

## #121 — Formato de erro no 404, no 405 e no 500

- PR: [#132 — formato de erro no 404, no 405 e no 500, e API em pt-br](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/132).
- Ferramenta: Claude (Anthropic).
- Apoio: testes em `backend/tests/test_formato_de_erros.py`, traduções `nao_encontrado` e `metodo_nao_permitido` no tratador (`backend/config/excecoes.py`), `handler404` e `handler500` em JSON para `/api/`, `LANGUAGE_CODE = "pt-br"` e docstring de `backend/config/erros.py`; na revisão, `/api` sem a barra final, `path_info` nos handlers e aviso do `code=` no 404 de rota com parâmetro.
- TDD: testes no commit 2557cfe, antes da implementação (7b448c4). Na `develop`, o módulo nem é coletado (`ImportError` do `erro_500`, importado no topo); isolando esse import, 8 dos testes novos falham (404 e 405 sem `codigo`, `Http404` do Django, rota inexistente da API em HTML, 500 em HTML e 403 padrão em inglês). Nos ajustes da revisão, testes no commit 8c7345f, que falhou com o `/api` sem a barra e com a API num subcaminho, antes da correção (e37fa07).
- Validação: `pytest` com 791 testes passando (depois dos ajustes da revisão) e cobertura de 97,67%, `ruff`, `bandit`, `manage.py check`, `makemigrations --check` e `spectacular --validate --fail-on-warn` (contrato sem mudança, inclusive depois da troca para `pt-br`) rodados localmente; resultado do CI no PR.
- Revisão humana: [revisão de Poviovsky](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/132#pullrequestreview-5927752431), aprovada com duas sugestões no registro (o vermelho do commit `test` e esta situação) e observações (`get_object_or_404`, `/api` sem a barra, `path_info`), aplicadas nos ajustes da revisão.
- Situação: `pt-br` adotado e [registrado na #121](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/121#issuecomment-6929024596); ajustes da revisão aplicados.
