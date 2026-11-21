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


## #123 — Limite de taxa no cadastro, no reenvio e no login

- PR: [PR #133](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/133).
- Ferramenta: Claude (Anthropic).
- Apoio: implementação a partir do guia da #123 e ajustes pedidos na revisão: testes em `backend/apps/cadastro/tests/test_limite_de_taxa.py`, `test_formato_de_erros.py` e `test_parametros.py`; `LimitePorIP` e `LimiteReenvioPorConta` (`apps/cadastro/limite_de_taxa.py`), `LimiteDeTaxaConfig`, tradução `throttled` → `limite_excedido`, `NUM_PROXIES` e `CACHES` (cache em banco) no `settings.py`, migration `0003_tabela_do_cache`, 429 no `openapi.yaml`, fixture `db` no teste de CSRF do login atrás do proxy, linhas do Anexo A e notas do C4 N4 4b e 4c. Na revisão: vaga do reenvio por conta gasta só quando o e-mail sai (`enviar_link` devolve se saiu), log quando o contador não é gravado (o `set` do `DatabaseCache` devolve `None` sempre, então a gravação é conferida lendo a chave de volta), IPv6 agrupado por /64, `MAX_ENTRIES` de 100 mil, fixture `cache_limpo` no `conftest.py`, testes do meio da janela e textos (formato do limite, mensagem do 429, `Retry-After` no 429 do login, `NUM_PROXIES` com o Caddy como único proxy).
- TDD: testes no commit ed4e659, antes da implementação (f83a4e7). Com só o `LimiteDeTaxaConfig` provisório (para o módulo importar), 32 dos testes novos falham: nenhuma rota dá 429, o `NUM_PROXIES` e o `CACHES` não existem, o `Throttled` sai como `{"detail": ...}` e o contrato não tem o 429. Nos ajustes da revisão, testes no commit e899935, antes da correção (3668dec): 8 falham (vaga gasta com o SMTP fora, `enviar_link` sem retorno, IPv6 sem agrupar, `MAX_ENTRIES` de 10 mil e falha de gravação sem log); os testes de "pedido normal não gera log de erro" passam ali e travam o falso alarme que conferir o retorno do `set` causaria.
- Validação: `pytest` com 857 testes passando (depois do recheck) e cobertura de 97,79%, `ruff`, `bandit`, `makemigrations --check` (sem mudança), `migrate` num banco novo (cria `cache_bandejao`) e `spectacular --validate --fail-on-warn` (diff de 16 linhas no PR, só nos três 429, e mais 2 na revisão, no 429 do login) rodados localmente; resultado do CI (incluindo `testes-mysql`) no PR.
- Revisão humana: revisão de AlvaroBento12 [Revisão de Álvaro Bento](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/133#issuecomment-6934287007), sem bloqueio, com dois ajustes pedidos (docstring do formato e vaga gasta na falha do SMTP) e cinco sugestões, todas aplicadas nos ajustes da revisão. A sugestão de conferir o retorno do `cache.set` foi aplicada com leitura de volta, porque o `set` do `DatabaseCache` devolve `None` mesmo quando grava. No recheck [recheck](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/133#issuecomment-6937500372), um ajuste: a leitura de volta conferia só se a chave existia, o que não pegava a falha a partir da 2ª gravação da janela (a linha antiga continuava lá). Agora confere se o horário do pedido chegou à lista, com 1 s de folga para pedidos simultâneos; testes no commit 909a8e0 (3 falham antes) e correção em 9cff7e6.
- Situação: números dos limites conforme a proposta do guia (seção 4.1), a confirmar com o grupo na #123.


## Skills — pr-review-toolkit e uso das skills

- PR: [#151 — Skills: pr-review-toolkit e uso das skills](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/151).
- Ferramenta: Claude (Anthropic).
- Apoio: cópia do plugin `pr-review-toolkit` (comando `review-pr` e seis agentes) para `SKILLS/pr-review-toolkit/`, atualização do `SKILLS/README.md`, criação do `SKILLS/USO-DAS-SKILLS.md`, renomeação de `SKILL(1).md` e `SKILL(2).md` para `SKILL.md` e inclusão do `README.md` e da pasta `references/` da `c4-architecture`, que faltavam no repositório (cópia do `softaworks/agent-toolkit`).
- TDD: não se aplica (só documentação, sem código).
- Validação: caminhos citados no `USO-DAS-SKILLS.md` conferidos no repositório; arquivos do plugin conferem com a versão 1.0.1 instalada.
- Revisão humana: [revisão de Poviovsky](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/151#pullrequestreview-5942574990), aprovada com ajustes (licença MIT da `c4-architecture`, link do PR e vírgula neste registro, convenção de commit de revisão, pasta `review-status` em minúsculas e aviso da dependência no `SKILLS/README.md`), aplicados nos ajustes da revisão.
- Situação: ajustes da revisão aplicados; aguardando nova revisão.


## BD-04 — Parâmetros do Anexo A

- PR: [#134 — Parâmetros do Anexo A](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/134). Issue: #90.
- Ferramenta: ChatGPT.
- Apoio: consulta dos requisitos e arquitetura, elaboração de testes, centralização das configurações, refatoração dos consumidores de cadastro e tratamento da revisão pelo CMD.
- TDD inicial: testes antes das implementações. Exemplos: fuso (`9a9b151` → `0339bb8`), horários (`293121a` → `1c9e19d`), login (`b1858d7` → `368e61f`), confirmação/exclusão de pendentes (`608dc1c` → `20e8b9b`) e parâmetros complementares (`1fe2daf` → `fdc1bce`).
- Validação inicial: após integrar a develop em `aaaeb0d`, SQLite com 844 testes aprovados e 1 ignorado, específico de MySQL. Cobertura de `apps`, incluindo branches, exibida como 98%; esse relatório não mede `config/`. Ruff check e format check aprovados.
- CI inicial: [Backend CI aprovado no commit 25e07d5](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/44001699240), incluindo SQLite, MySQL, lint e segurança.
- Revisão humana: [revisão inicial de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/134#issuecomment-6937768384) e [recheck do commit 7c7134e](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/134#issuecomment-6953993502). Os ajustes de código foram aceitos; restou a atualização deste registro antes do merge. Sugestões opcionais podem permanecer fora do PR; arquitetura acompanhada na #153.
- TDD da revisão: testes sem reload em `e667609`, com duas falhas pelos valores fixados no import; implementação em `4abd9b8`. Os 56 testes selecionados passaram após a correção.
- Outros ajustes: alias de validade removido em `360febc`, com 36 testes aprovados; regressões da virada do ano e bordas configuradas do login em `cf81770`, com 10 testes aprovados. Essas regressões passaram desde a inclusão, pois verificam comportamentos já existentes.
- Parâmetros pendentes: datas de término dos semestres sem entradas; precisão mínima e idade máxima da posição sem valores definidos. Nenhum valor foi inventado.
- Limites: disponibilizar parâmetros não implementa endpoints, agendamentos ou integração com o front-end. A mudança de fuso altera o comportamento das datas locais; a classificação do PR já foi corrigida para refletir isso.
- Arquitetura: ajustes da revisão reservados ao Álvaro, para acompanhamento em issue exclusiva da BD-04. Os arquivos de arquitetura não foram alterados nesta rodada.
- Validação após os ajustes da revisão e integração da develop em `440137c`: SQLite com 930 testes aprovados e 1 ignorado, específico de MySQL; cobertura de `apps`, incluindo branches, de 97,78% (não mede `config/`); Ruff check aprovado e 128 arquivos com formatação aprovada.
- Situação: ajustes aplicados e recheck registrado; [CI aprovado no commit 7c7134e](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/44117753566), incluindo MySQL. Arquitetura acompanhada separadamente na #153. Conferir os checks do último commit antes do merge.

## BE-09 — Check-in (`POST /api/checkins/`)

- PR: [#154 — BE-09: check-in](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/154). Issue: #136.
- Ferramenta: Claude (Anthropic), no Claude Code.
- Apoio: leitura da issue, do C4 N4 da Fila (4a) e da Gamificação (4a); testes da distância, da janela de horário, do `CheckinService` e do endpoint; implementação de `CheckinView`, `CheckinService`, `CheckinRepository`, `ConfirmacaoLocalizacaoService`, `DistanciaGeografica`, `Coordenadas`, `LocalizacaoRUConfig`, `JanelaCheckinValidator` e da versão mínima de `PontuacaoService.registrar_contribuicao`; 400 `dados_invalidos` no `openapi.yaml`; nota da BE-09 no C4 N4 da Fila.
- TDD: testes no commit 6769319, que falhou por falta dos módulos (`ModuleNotFoundError` de `apps.fila.distancia_geografica`), antes da implementação (9de4de8).
- Sabotagem manual: 14 defeitos colocados à mão nos módulos do check-in (raio `>` trocado por `>=`, confirmação desativada ignorada, borda do horário, horário em UTC, faixa de 15 min, data em UTC, tentativa não gravada, `IntegrityError` não convertida, aviso conferido dentro do `try`, centro do campus no lugar do centro do RU, entre outros). Quatro sobreviveram na primeira rodada: dois eram lacunas (data em UTC e centro do campus) e ganharam testes; os outros dois eram equivalentes (o savepoint redundante do repositório, que foi retirado, e o aviso conferido dentro do `try`, que não grava tentativa de qualquer forma).
- Validação: `pytest` no SQLite com 998 testes passando e 1 ignorado (específico do MySQL), cobertura de `apps`, incluindo branches, de 97,98%; `ruff check`, `ruff format --check`, `bandit`, `makemigrations --check` e `spectacular --validate --fail-on-warn` rodados localmente; resultado do CI (incluindo `testes-mysql`) no PR.
- Revisão humana: [revisão de Poviovsky](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/154#pullrequestreview-5945731158), com um pedido de mudança e sugestões.
- Ajustes da revisão: o teste de RI09 procura os dígitos da posição que cada caso envia (no `fora-do-raio` a latitude não era conferida; a sabotagem do revisor, um log da latitude no ramo "fora do raio", passou a ser pega), teste de que todo motivo de recusa tem mensagem, `tipoRefeicao` como `ChoiceField` (enum no `openapi.yaml`), `campus` como `PrimaryKeyRelatedField` e comentário sobre a `IntegrityError` no `CheckinRepository`. TDD: testes em 0ee7262, com o teste do enum falhando, antes da implementação (612e6b0). As perguntas de regra (RI03 por campus e check-in em dia sem RU) ficaram para o grupo decidir.
- Validação após os ajustes: `pytest` no SQLite com 1000 testes passando e 1 ignorado, cobertura de `apps` de 97,97%; `ruff`, `bandit`, `makemigrations --check` e `spectacular --validate --fail-on-warn` aprovados localmente.
- Situação: ajustes da revisão enviados; aguardando o CI do último commit e o recheck.

## #135 — Ajustes finais de arquitetura do BD-03

- PR: [#152 — CHECKs de CAMPUS no erDiagram e confirmacao_ativa na LocalizacaoRUConfig](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/152).
- Ferramenta: Claude (Anthropic), com a skill `c4-architecture`.
- Apoio: sugestões 3 e 4 da [segunda revisão do PR #129](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/129#issuecomment-6937610684): CHECKs de `raio_confirmacao_metros` e `raio_deteccao_metros` no erDiagram do Nível 4 do banco e `confirmacao_ativa` na lista de campos lidos pela `LocalizacaoRUConfig`, no Nível 4 da exposição do cardápio.
- TDD: não se aplica (só documentação).
- Validação: anotações conferidas com as constraints `campus_raios_nao_negativos` e `campus_confirmacao_ativa_exige_raio_positivo` do model e da migration `0003`, e com `LocalizacaoRUConfig.confirmacaoAtiva(campus)` do Nível 4 da Fila; diagramas dos dois documentos renderizados sem erro no Mermaid 10.9.3 (versão usada pelo docsify) e no 11.4.1.
- Revisão humana: [revisão de eusojj](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/152#pullrequestreview-5943164631), sem bloqueio, com um ponto importante e quatro sugestões. Aplicadas: `> 0 se confirmacao_ativa` no erDiagram e nomes das constraints na tabela de campos de `CAMPUS`. Sem mudança: o `classDiagram` da exposição do cardápio não tem `LocalizacaoRUConfig` (ela só aparece no Nível 4 da Fila, que já tem `confirmacaoAtiva`); o formato "descrição; CHECK" segue o restante do erDiagram; `Closes` é o padrão dos PRs do grupo.
- Situação: ajustes da revisão aplicados e `develop` integrada; aguardando nova revisão.

## #153 — Arquitetura da BD-04 alinhada à revisão do PR #134

- PR: [#155 — BD-04 alinhada à revisão do #134](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/155).
- Ferramenta: Claude (Anthropic), com a skill `c4-architecture`.
- Apoio: itens 3, 5, 9 e 11 da [revisão do PR #134](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/134#issuecomment-6937768384) e o recheck do commit `7c7134e`: `ParametrosCadastroConfig` completa no diagrama 4c, sem o `MAX_POR_HORA` do `SolicitacaoRedefinicaoTracker`; setas de `MatriculaValidator` (4a), `ConfirmacaoEmailService` e `ExclusaoCadastroPendenteJob` (4b) para a configuração; acesso por instância a `duracao_segundos` e `url_pagina`, sem `reload`; nota do alias `VALIDADE_DO_LINK` removida; separação entre `ParametrosLeitorConfig` e `FonteCardapioConfig` no N3 e no N4c do Leitor; Bandeja de Ouro "fora do escopo atual por decisão do backlog" no N3; linha da BD-16 no backlog alinhada a essa separação.
- TDD: não se aplica (só documentação).
- Validação: diagramas e notas conferidos com `backend/config/parametros.py` e com os consumidores na `develop` (`0343362`); os 8 diagramas dos três documentos renderizados sem erro no Mermaid 10.9.3 (versão usada pelo docsify) e no 11.4.1. O diagrama 4c de Cadastro já não renderizava na `develop` (o `;` no rótulo `abrir(), no POST; encerrarAtual(), no DELETE`); o `;` virou ", e".
- Revisão humana: [revisão de Poviovsky](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/155#pullrequestreview-5947760372), com um pedido de mudança e duas sugestões, e [aprovação](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/155#pullrequestreview-5956708152) depois dos ajustes.
- Ajustes da revisão (08e8406): `ParametrosCadastroConfig` e a seta do `MatriculaValidator` retiradas do 4a de Cadastro, que voltou ao limite de 20 elementos (o ano mínimo segue nas notas e na tabela de parâmetros); seta `SessoesDaConta ..> ParametrosSessaoConfig` tracejada no 4c, com a nota de que quem aplica a duração é o Django (`SESSION_COOKIE_AGE`); nota no Leitor 4c de que as classes entram na BE-12 e de que a convenção cheia/tracejada do Cadastro 4c não vale ali. [Resposta à revisão](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/155#issuecomment-6978749760).
- Validação após os ajustes: os 8 diagramas dos três documentos passam no `mermaid.parse` do Mermaid 10.9.3, sem erro.
- Situação: revisão aprovada; pronto para o merge.

## BD-05 — Docker e publicação

- PR: [#157 — BD-05: Docker e publicação](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/157).
- Ferramenta: Claude (Anthropic).
- Apoio: `backend/Dockerfile` e `entrypoint.sh` (Gunicorn, espera do MySQL, `migrate` e `collectstatic`), `requirements-prod.txt`, `frontend/Dockerfile` (build do PWA na imagem do Caddy), `Caddyfile`, `docker-compose.yml`, `STATIC_ROOT` no `settings.py`, instruções em `docs/deploy/deploy-producao.md` e primeiro deploy na VM.
- TDD: não se aplica (infraestrutura de deploy, sem código de aplicação); os testes de settings e e-mail ficam no PR da dupla do banco.
- Validação: build do PWA com `VITE_USE_MOCK=false`, `collectstatic` e `check --deploy` em modo produção e `ruff` locais; na VM, `docker compose config`, `docker compose up -d --build`, PWA, `/api/campi/`, `/admin/` e `/static/` respondendo por HTTPS com certificado do Let's Encrypt, e teste de reboot com os três containers voltando sozinhos.
- Revisão humana: [revisão de eusojj](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/157#pullrequestreview-5966561757), com 3 pontos importantes e 7 sugestões.
- Ajustes da revisão: senha do root do MySQL num `.env.db` só do container `db`; healthcheck do backend, com o Caddy esperando por ele; prazo de 60 s por relógio no `entrypoint.sh`, que mostra o último erro do banco; cabeçalhos de segurança no PWA e no `/static/`; `.env.db`, `staticfiles/` e os caches do ruff e do pytest no `.gitignore`; lista completa das variáveis no guia de deploy, `/api/campi/` na conferência, certificado pedido na subida e aviso sobre a troca de senhas; nomes dos recursos da Azure retirados do guia. O `/admin/` público e o SSH aberto foram para a [#158](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/158); o backup já é a BD-15 do backlog.
- Validação dos ajustes: a VM passou a rodar a própria branch do PR; `docker compose config` e `up -d --build`; backend `healthy` e sem o `MYSQL_ROOT_PASSWORD` no ambiente; as mesmas respostas por HTTPS; cabeçalhos de segurança no PWA, no `/static/` e na API, sem duplicar os do Django.
- Segunda revisão: [aprovação de eusojj](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/157#pullrequestreview-5967539868), com 7 sugestões. Aplicadas a 1 e da 3 à 6: o `entrypoint.sh` confere que o Django usa o MySQL (a mesma checagem do CI) antes de tudo; cada tentativa de conexão tem `timeout` de 10 s e mostra a última linha do erro; `printf` no lugar do `echo` do dash; e o guia ganhou o `--force-recreate db` e a migração do `MYSQL_ROOT_PASSWORD` de um `.env` antigo. A 2 (healthcheck por HTTP) e a 7 (`lb_try_duration` no Caddy) ficaram para depois.
- Validação da segunda revisão: na VM, backend `healthy`; com `DB_ENGINE` vazio ou `sqlite`, o backend para na hora com a mensagem do MySQL; com host e senha errados, cada tentativa mostra o motivo e o backend desiste no prazo.
- Atualização com a `develop` (FE-01, #119): o `apiClient` passou a ligar o simulado só no servidor de desenvolvimento, então o `VITE_USE_MOCK` saiu do `frontend/Dockerfile` (`d24f27a`). Validação: o build sem a variável não leva o código do simulado; na VM, o PWA reconstruído responde, e o `/api/sessao/` devolve 401 sem login, vindo da API real.
- Situação: aprovado; sugestões da segunda revisão aplicadas e branch atualizada com a `develop`.

## ADR 0015 — Permissões de agentes de IA

- PR: [#156 — ADR 0015: permissões de agentes de IA no repositório](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/156).
- Ferramenta: Claude (Anthropic).
- Apoio: commit da ADR 0015 e das linhas no `docs/_sidebar.md` e no `README.md`, abertura do PR e ajustes da revisão: decisão reescrita (sem commit ou push direto na `main` e na `develop`, merge por um integrante depois da revisão de alguém diferente de quem operou o agente, force-push incluído, branches de trabalho fora da regra), status de volta para "Proposta", data do PR com a da redação entre parênteses, Contexto apoiado na Definition of Done, argumento da alternativa alinhado à ADR 0013, referências trocadas pelas que tratam do tema e ponto em aberto sobre "Require approvals".
- TDD: não se aplica (só documentação).
- Validação: links do sidebar e do README conferidos; afirmações da ADR conferidas com a ADR 0013, o `backlog.md` §1.4, o `plano-de-testes.md` §3.10 e o README (Gitflow).
- Revisão humana: [revisão de eusojj](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/156#pullrequestreview-5967413548), com pedido de mudanças, e [resposta à revisão](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/156#issuecomment-6999016626).
- Proteção da `main`: a `main` não tinha proteção nenhuma. Em 2026-11-19, a pedido de AlvaroBento12, o agente aplicou nela, pela API do GitHub, as mesmas regras da `develop` (PR obrigatório, os 4 jobs do CI verdes, branch atualizada, sem force-push e sem exclusão, 0 aprovações, sem valer para administradores), e a ADR passou a descrever a proteção das duas branches.
- Segunda revisão: [aprovação de eusojj](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/156#pullrequestreview-5969631334), com 3 pontos antes do merge e 4 sugestões. Aplicados os 3 pontos e as sugestões 4 e 5: PR #156 citado no lugar de "neste PR"; exceção dos administradores nas Consequências; status "Aceita"; mutação descrita no futuro, porque ainda não há job de mutação no CI, e sem o trecho de documentação, que a ADR 0013 e o §3.10 não citam; a ADR fixa o mínimo para o trabalho com agentes sem dispensar a DoD. As sugestões 6 (configurações do repositório) e 7 (redação) ficaram de fora.
- Situação: revisão aprovada; pronto para o merge. A decisão sobre "Require approvals" fica para a equipe.

## BD-05 — Banco, settings de produção e e-mail

- PR: [#203 — feat(banco): MySQL, usuários, settings de produção e e-mail (BD-05)](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/203).
- Ferramenta: Claude (Anthropic).
- Apoio: `db/conf.d/bandejao.cnf` (`utf8mb4` e `READ-COMMITTED`), `db/init/10-usuarios.sh` (usuário da aplicação com permissões mínimas, papel `equipe_moderacao` e primeiro usuário da equipe), variáveis `DJANGO_*` no `settings.py` com `DJANGO_ALLOWED_HOSTS` obrigatório em produção e parada na subida com os nomes antigos, `.env.example`, `pytest.ini`, CI, `.gitattributes` e seções Banco e E-mail no guia de deploy; decisão de não exigir TLS na conexão com o banco registrada no PR.
- TDD: testes antes do código (`4f41971` antes de `7b09297`): settings lidos do ambiente, envio pelo SMTP do Brevo com `smtplib` simulado e conferência do `.cnf` e das permissões do script.
- Validação: `pytest` local com 1026 testes passando (1 pulado), `ruff check` e `ruff format --check`, `manage.py check` e `check --deploy` com o ambiente de produção; script de usuários conferido com `sh -n` e com o `mysql` simulado.
- Revisão humana: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/203#issuecomment-7016721088), sem bug bloqueante. Ajustes aplicados com TDD (testes no commit `test(banco)` antes do `fix(banco)`): erro do `mysql` no script sai com status 1 e mensagem; `REVOKE` também com o `_` escapado e usuário e banco escapados no SQL; `EMAIL_BACKEND` diferente do SMTP e `DEFAULT_FROM_EMAIL` faltando param a subida em produção; `SHOW GRANTS` obrigatório depois do deploy no guia; ADR da criptografia corrigida (é o item do backlog); aviso do `DELETE` x `RemoverContaCommand`; comentários desatualizados; testes do script com um `mysql` falso, de `DJANGO_DEBUG`, de vários nomes antigos e de nome antigo vindo do `.env`, e meta-teste das variáveis do conftest. Ficou para depois: rodar o CI MySQL com o usuário restrito.
- Validação na VM (19/11, guiada pelo Claude, comandos rodados por AlvaroBento12): `.env` com os nomes `DJANGO_*` e o `DEFAULT_FROM_EMAIL`, `.env.db` com o usuário da equipe; script de usuários rodado à mão (status 0); `SHOW GRANTS` sem `ALL PRIVILEGES` no `DB_USER`, papel `equipe_moderacao` no usuário da equipe e `READ-COMMITTED`; `migrate` com o usuário restrito; `check --deploy` só com W004 e W008; `sendtestemail` pelo Brevo recebido. O `Ssl_cipher` da conexão do backend veio vazio (sem TLS), dentro do que a ADR 0008 considera suficiente; a correção do guia para registrar isso está no [#210](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/210).
- Situação: mesclado em 19/11 e validado na VM.

## BD-16 — Origem do cardápio por campus

- Issue: [#161](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/161). PR: [#162 — origem do cardápio por campus](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/162).
- Ferramenta: Claude (Anthropic).
- Apoio: colunas `rotulo_pagina_ru` e `prefixo_arquivo_pdf` em `CAMPUS` (NOT NULL, UNIQUE), tabela `FONTE_CARDAPIO` (UNIQUE por campus e semana, `ON DELETE CASCADE` no campus), migration `cardapio.0004_origem_cardapio_bd16` com o preenchimento dos campi existentes, fixture `campi` com os rótulos e prefixos do Anexo A, ajuste dos helpers de teste que criam campus e documentação (Nível 4 do banco e README das fixtures), conforme a ADR 0014.
- TDD: testes no commit `92c2f6a`, antes da implementação; falharam na coleta porque `FonteCardapio` ainda não existia.
- Validação local (SQLite): `pytest` com 1012 testes aprovados e 1 ignorado (específico do MySQL), cobertura de 97,94% (mesmos números depois dos ajustes da revisão); `ruff check`, `ruff format --check` e `makemigrations --check` sem achados. Migration no MySQL: job `testes-mysql` do PR.
- Checklist do Plano de Testes (3.10): os testes cobrem os valores do Anexo A, as duas UNIQUE de `CAMPUS`, a UNIQUE e o CASCADE de `FONTE_CARDAPIO` e a data migration com os 5 campi e com um campus fora do Anexo A.
- Revisão humana: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/162#pullrequestreview-5975331117), aprovando a implementação e pedindo a resolução do conflito neste arquivo com o #157.
- Ajustes da revisão: a `develop` foi trazida para a branch e as duas seções foram mantidas; a reserva da migration para campus fora do Anexo A passou a ser `sem-rotulo-<id>` e `sem-prefixo-<id>` (teste em `cb46283`, correção em `f1a40df`; o caso do teste, um "Ceilandia" sem acento, falhava no MySQL já no UNIQUE de `nome`, por causa da collation, e foi trocado em `5f87d02` por um campus "Fazenda" ao lado da FAL, que colide com o prefixo do Anexo A nos dois bancos com a reserva antiga, conferido localmente); o Nível 4 do banco registra que a UNIQUE é exata no SQLite e segue a collation no MySQL.
- Segunda revisão: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/162#pullrequestreview-5979055969), que confirmou os ajustes e apontou um novo conflito neste arquivo com o #156 (ADR 0015). A `develop` foi trazida de novo, com as duas entradas mantidas.
- Aprovação: [aprovação de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/162#pullrequestreview-5986095373). Depois dela, a `develop` recebeu o #203 (BD-05 do banco), e a branch foi atualizada de novo, com as entradas mantidas.

## BD-10 — Índices da previsão e do ranking no MySQL

- Issue: [#150](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/150). PR: [#160 — índices da previsão e do ranking no MySQL](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/160).
- Ferramenta: Claude (Anthropic).
- Apoio: teste `backend/tests/test_indices_bd10.py` (dados de teste em volume, `ANALYZE` e `EXPLAIN` das consultas de previsão de pico, espera estimada e ranking nos dois bancos), passo "EXPLAIN dos índices (BD-10)" no job `testes-mysql`, documento `docs/arquitetura/banco-de-dados/indices-bd10.md` com os planos e as regras para a BE-15 e a BE-17, referência no Nível 4 do banco e nota no plano de testes.
- TDD: teste no commit `0a4fd90`, antes da documentação e do passo do CI. Os índices já existiam desde a BD-01, então o vermelho foi comprovado localmente com uma migration de prova (descartada) que remove os dois índices: os três testes de plano falharam (índice de `data` na previsão e UNIQUE de pontos no ranking).
- Validação local (SQLite): `pytest` com 1005 testes aprovados e 1 ignorado (específico do MySQL), cobertura de 97,97%; `ruff check` e `ruff format --check` sem achados.
- Achado no MySQL 8.4 (CI): a previsão usou o índice desde a primeira execução, mas o ranking com join não usava `pontos_semestre_ranking_idx` (lia todas as contas e ordenava em arquivo temporário). Um teste de diagnóstico temporário (commits `e88e6e8` e `d8c3643`, removido depois) comparou join, `EXISTS`, `IN`, histogramas, dicas de otimizador e `EXISTS` dentro de `CASE`. Só o `EXISTS` dentro de `CASE`, sem `select_related`, usa o índice só com o ORM; a consulta do teste e as regras para a BE-17 passaram a ter essa forma (`410de07`).
- Correção do teste no MySQL (`be9d85f`): o `bulk_create` não devolve o id das contas no MySQL, e a fixture passou a recarregá-las do banco.
- Validação no MySQL: planos da [execução 44466578120](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/44466578120) (`410de07`, 1007 testes aprovados, contando o diagnóstico temporário) no `indices-bd10.md`; depois da remoção do diagnóstico, [execução 44467642301](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/44467642301) (`b0eab3b`) com 1006 testes aprovados no `testes-mysql`.
- Checklist do Plano de Testes (3.10): os testes conferem o índice escolhido e também o resultado das consultas, para o plano não ser de uma consulta vazia ou diferente da previsão e do ranking.
- Revisão humana: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/160#pullrequestreview-5975589822), sem bloqueio para o merge, com três pontos a melhorar e três sugestões.
- Ajustes da revisão (`394382b`): o teste do ranking compara a consulta com o top 10 calculado em Python, com `atualizado_em` embaralhado e um empate no topo fora da ordem dos ids (um desempate por id ou uma elegibilidade que descarte contas faz o teste falhar, conferido localmente); o ranking no MySQL também não pode ter `Using temporary`; o parse do plano do SQLite aceita `SEARCH TABLE`; o passo do EXPLAIN só roda se os testes do MySQL rodaram; os números deste registro foram corrigidos. A `develop` foi trazida para a branch para resolver o conflito neste arquivo com o #157.
- Segunda revisão: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/160#pullrequestreview-5979299475), que confirmou os ajustes e apontou um novo conflito neste arquivo com o #156 (ADR 0015). A `develop` foi trazida de novo, com as duas entradas mantidas, e a sugestão opcional foi aplicada: o teste do ranking busca os usuários elegíveis numa consulta só, no lugar de uma consulta por linha.
- Aprovação: [aprovação de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/160#pullrequestreview-5986084888), no `f0af2b5`. Depois dela, a `develop` recebeu o #203 (BD-05 do banco), e a branch foi atualizada de novo, com as entradas mantidas.
- Depois do merge do #162 (BD-16): a `develop` foi trazida de novo, com a entrada da BD-16 antes desta, e `_criar_campi` passou a preencher `rotulo_pagina_ru` e `prefixo_arquivo_pdf`, as colunas UNIQUE que a BD-16 criou no `Campus`.
- Situação: aprovado; pronto para o merge.

## BE-20 — Login com e-mail institucional

- PR: [#204 — BE-20: login com e-mail institucional e senha](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/204). Issue: #201.
- Ferramenta: Claude (Anthropic).
- Apoio: a partir do guia da BE-20, testes do login, do reenvio, do `ContaRepository.buscar_por_email`, dos serializers e do limite de taxa com `emailInstitucional`; implementação de `buscar_por_email` (no lugar de `buscar_por_identificador`), da normalização e da conferência de domínio no `LoginService` (`EmailInstitucionalValidator`, ADR 0002), de `conta_para_reenvio(email=..., token=...)`, das mensagens do 422 e do 401 genérico (`config/excecoes.py`, troca aprovada por AlvaroBento12) e das descrições do `extend_schema`; `openapi.yaml` regerado.
- TDD: testes no commit 0117583, com 103 testes falhando e 6 erros antes da implementação (corpos ainda com `matriculaSiape` no código e `buscar_por_email` inexistente).
- Validação: `pytest` no SQLite com 1029 testes passando e 1 ignorado (específico do MySQL), cobertura de `apps`, incluindo branches, de 97,99%; `ruff check`, `ruff format --check`, `bandit`, `makemigrations --check` (sem migration) e `spectacular --validate --fail-on-warn` aprovados localmente; diff do `openapi.yaml` só em `POST /api/sessao/` e `POST /api/reenviar-confirmacao/`; resultado do CI (incluindo `testes-mysql`) no PR.
- Revisão humana: revisão de AlvaroBento12 no PR #204, sem bug no código de produção, com dois pontos antes do merge (marcadores deste registro e trava do login sem teste) e sugestões.
- Ajustes da revisão: marcadores deste registro preenchidos; testes da trava (`select_for_update` pedido pelo `LoginService` na linha da conta, e só com `travar=True` no `buscar_por_email`); no reenvio com `emailInstitucional` e `token`, o token passa a ser tentado quando o e-mail não acha conta (a resposta continua sempre 200); testes de log do login e do reenvio procurando qualquer `@` (estudante, professor e e-mail de fora, inclusive com falha do SMTP); reenvio com e-mail só de espaços ou com mais de 254 caracteres; conta inexistente `@unb.br` com a mesma resposta da senha errada. Saiu o teste com `hasattr` do `buscar_por_identificador`. `IdentificadorInvalidoError` e `MENSAGEM_IDENTIFICADOR` mantêm o nome, como o guia decidiu. O 500 do reenvio como oráculo de conta pendente já existia antes do PR e ficou registrado na resposta à revisão, para uma issue separada.
- TDD dos ajustes: testes no commit 98ca6f2, com 2 testes falhando (token ignorado no reenvio com os dois campos) antes da implementação. Os testes da trava já passavam, porque a trava existe; sabotagem manual confirmou que eles pegam a regressão: sem o `if travar:`, sempre com trava e com `travar=False` no `LoginService`, cada caso derrubou de 1 a 2 testes.
- Validação após os ajustes: `pytest` no SQLite com 1038 testes passando e 1 ignorado, cobertura de `apps` de 98,08%; `ruff`, `bandit`, `makemigrations --check` e `spectacular --validate --fail-on-warn` aprovados localmente; o `openapi.yaml` só mudou na descrição do `ReenvioConfirmacaoEntradaRequest`.
- Situação: aprovado por AlvaroBento12 no recheck, com CI verde (incluindo `testes-mysql`); o 500 do reenvio como oráculo ficou na #205; merge aguardando a FE-03 (#101).

## FE-03 — Sessão ao abrir o app e login por e-mail institucional

- Issue: [#101](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/101). PR: [#207 — FE-03: authStore e telas de conta](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/207).
- Ferramenta: Claude (Anthropic).
- Apoio: `carregarSessao()` no `authStore` (`GET /api/sessao/` ao abrir o app, com tempo limite de 3 s e controle por geração para respostas atrasadas), guardas do router reunidos em `instalarGuardas`, opção `avisarSessaoPerdida` no `apiClient`, login e reenvio pelo e-mail institucional nas telas, na store e no servidor simulado (contrato do #204, BE-20, #201) e testes do fluxo 4b com as telas montadas. Os patches foram gerados pela IA e aplicados e commitados pela autora.
- TDD: cada `feat`/`fix` veio depois de um commit `test`: `7363c2b` (sessão e fluxo 4b), `a75afdb` (tempo limite), `860c009` (e-mail institucional), `c1d610e` (guardas, log e geração) e `2822f07` (reenvio no login). Os testes novos falharam antes da implementação, e uma sabotagem manual (tirar a geração do `limpar`, tirar a checagem da geração e pôr o limite em 0) derrubou pelo menos um teste em cada caso.
- Validação: `npm run test:ci` com 191 testes passando e cobertura de 85,71% das linhas e 74,39% dos ramos; `npm run lint:ci` sem achados; `npm run build` sem erro.
- Revisão humana: duas revisões de AlvaroBento12 no PR #207 (tempo limite da sessão, sincronia com o #204, guarda ligado no router do app, log no boot, geração no login, testes da geração e do RI09, comentários) e o comentário depois do merge do #204.
- Situação: ajustes das duas revisões aplicados; aguardando o recheck e o teste contra o backend real da `develop`.
 
 ## BD-05 — Registro da validação em produção

- Issue: [#91](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/91). PR: [#211 — docs(deploy): validação em produção e loaddata](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/211).
- Ferramenta: Claude (Anthropic).
- Apoio: seção "Validação em produção (20/11/2026)" no `docs/deploy/deploy-producao.md` e o passo do `loaddata campi marcadores` depois do primeiro deploy, além do roteiro dos comandos rodados na VM (estado dos serviços, HTTPS, porta 3306, permissões dos `.env` e reinício).
- TDD: não se aplica (só documentação).
- Validação: comandos rodados por Luís na VM em 20/11: serviços `Up` (`db` e `backend` `healthy`), `HTTP/2 200`, `www` com `301`, 3306 recusada de fora, `.env` e `.env.db` com `600`. `/api/campi/` devolvia `[]` antes do `loaddata` e passou a listar os 5 campi. Depois do `sudo reboot`, os três serviços voltaram sozinhos e a API continuou com os dados. Teste do IP real atrás do Caddy (`NUM_PROXIES = 1`): de uma rede (casa), o 11º pedido a `/api/reenviar-confirmacao/` deu 429 (limite de `10/hour` por IP); de outra rede (a própria VM, com IP público diferente), o pedido seguinte deu 200. Cada IP é contado separado, como pediu o Poviovsky no #91.
- Revisão humana: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/211). Ajustes aplicados: caractere invisível nas cercas, nome e região da VM fora do guia, `loaddata` no passo 3 e conferência da API pela lista dos 5 campi, número do PR, aviso de que o `loaddata` só roda na primeira subida e nome exato da entrada do AI-USAGE citada no guia.
- Situação: PR aberto; aguardando o merge do #210 (a entrada da BD-05 citada no guia vem dele) e o recheck de AlvaroBento12.

## DOC-12 — Login com e-mail institucional e senha

- Issue: [#202](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/202). PR: [#208 — DOC-12: login com e-mail institucional e senha](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/208).
- Ferramenta: Claude (Anthropic).
- Apoio: levantamento dos trechos que citavam o login por matrícula/SIAPE, redação da ADR 0016 e das notas nas ADRs 0002, 0007 e 0008, e atualização de requisitos (RF02.2, RF03, RF04.1, RN01, L16, Anexo A), Visão, glossários, aviso de privacidade, backlog, README e C4 (Cadastro N4, banco N4 e front).
- TDD: não se aplica (só documentação).
- Validação: os 16 diagramas Mermaid dos três C4 alterados renderizam sem erro no `mmdc` (Mermaid CLI, Mermaid 11.16.1); o site usa o Mermaid 10 pelo Docsify, e a sintaxe é a mesma dos blocos que já existiam. Uma varredura confirmou que nenhum documento descreve o login por matrícula/SIAPE, a não ser como comportamento do MVP. Os nomes conferem com o código da `develop`, onde já estão a BE-20 (#204) e a FE-03 (#207).
- Revisão humana: duas revisões de AlvaroBento12 no PR #208 (sobras no `README.md` e no `CONTEXT.md`, login que confere só o domínio, reenvio sem conferir o domínio, ADR 0016 aceita, aviso de privacidade, selos de release, Anexo B, Visão 5.1, backlog e este registro).
- Ajustes da revisão: `develop` trazida para o branch; sobras corrigidas e ADR 0016 na lista do `README.md`; RF03.1, ADR 0016, ADR 0002 e C4 dizem que o login confere só o domínio; reenvio documentado (e-mail fora do padrão não acha conta; com e-mail e token, vale o e-mail); `contaParaReenvio(email, token)`; nota sobre o nome `IdentificadorInvalidoError`; ADR 0016 aceita; selos *(Release 2)* no RF03.1 e no RF04.1, regra do login do MVP de volta à RN01 e ADR 0016 em ordem nas referências; Visão 5.1 com o login do MVP por matrícula/SIAPE; §11 do aviso de privacidade separando mudança de finalidade de ajuste, com o "revisado em 2026-11-19" no topo, sem nova ciência.
- Situação: ajustes aplicados; aguardando o recheck.

## BE-11 — Cardápio

- Issue: [#138](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/138). PR: #214 — BE-11: `GET /api/cardapio/` com RN05 e filtros.
- Ferramenta: Claude (Anthropic).
- Apoio: a partir do guia da BE-11 (21/11/2026), testes e implementação de `DietaSelecionada`, `FiltroDietaService`, `FiltroMarcadorService`, `HorarioRefeicaoResolver` (RN05 da R2, horários lidos do `HorariosRefeicaoConfig`), `SemanaCardapioResolver` e `Semana` (semana vigente pela `FonteCardapio`), `RefeicaoRepository` (só leitura, com prefetch de categorias, pratos e marcadores), `CardapioQueryService` e `CardapioView` (validação e 400 `parametros_invalidos`), além dos objetos de resposta (`CardapioFiltrado`, `CategoriaFiltrada`, `PratoFiltrado`, `StatusCardapio`) e da nota de implementação no C4 4a (`c4-nivel-4-exposicao-cardapio.md`). O código foi gerado pela IA; os commits foram aplicados pelo autor do PR.
- TDD: cada `feat` veio depois de um commit `test` com os testes da etapa falhando (`ImportError` nas seis primeiras etapas; 53 testes falhando na da view, que ainda devolvia 501). A sequência foi conferida commit a commit: o arquivo de teste novo falha no commit `test`, e os testes do app `cardapio` passam no `feat` seguinte.
- Sabotagem manual (módulo crítico): 23 alterações, em 14 grupos de regras (dietas permitidas, `all` por `any`, categoria vazia, filtro desativado com alérgenos indisponíveis, início e fim do horário, refeição encerrada, intervalo da semana, próximo dia com serviço, conferência da `FonteCardapio`, ordem do dia pedido, item vazio e nome desconhecido em `marcadores`, dia fora da semana, campus não numérico). Na primeira rodada, uma sobreviveu (o dia pedido com `semana` e sem `dia`): o teste foi corrigido no commit `test` da etapa, e as 23 passaram a derrubar ao menos um teste.
- Validação local (SQLite): `pytest` com 1284 testes aprovados e 1 ignorado (específico do MySQL; eram 1102 na `develop` em `9ef7f90`), cobertura de `apps` (com branches) de 98,31%, e 100% nos módulos novos; `ruff check`, `ruff format --check`, `bandit -lll`, `makemigrations --check` e `spectacular --validate --fail-on-warn` aprovados. O `openapi.yaml` gerado é idêntico ao do repositório (contrato sem mudança). `semgrep`, `pip-audit` e `testes-mysql` ficam com o CI.
- Checklist do Plano de Testes (3.10): toda asserção é sobre o resultado; os valores esperados saem do RF08, do RF09, da RN05 e do Anexo A (tabela 9.2 do guia); nenhum mock da própria unidade (só o relógio, e um resolvedor de semana falso no teste da conferência da `FonteCardapio`); um teste garante que o resolver usa a mesma janela do `JanelaCheckinValidator` no início e no fim de cada refeição.
- Revisão humana: revisão de AlvaroBento12 no PR #214, com o pr-review-toolkit: três pontos antes do merge (parâmetro repetido ou com nome errado ignorado em silêncio, 500 com datas nos extremos do calendário e `leitura_falhou` publicado com o filtro de marcador ativo), seis médios e sugestões.
- Ajustes da revisão: 400 para parâmetro fora dos seis do contrato (ex.: `marcador`, `marcadores[]`) ou repetido, e para `semana` ou `dia` fora de 2000-01-01 a 2099-12-31; refeição com `leitura_falhou` sai `nao_publicado`; próximo dia com serviço buscado em até 7 dias; avisos no log para refeição sem a linha da `FonteCardapio` e para categoria com dietas misturadas; descrições do OpenAPI de `semana`, `dia`, `marcadores` e do 400 (`openapi.yaml` regerado, só descrições); diagrama do C4 4a com as assinaturas do código e a classe `RefeicaoPadrao`, e a nota com as decisões sobre `semana` (qualquer data, só escolhe o dia), semana cruzada pelo item 5 da RN05 e refeição pedida num dia sem serviço; comentários corrigidos. Novos testes das bordas apontadas (`dia_pedido` no início e no fim da semana, `dia` em `semana - 1`, `semana`, `semana + 6` e `semana + 7`, UTC no serviço e em `refeicao_terminou`, refeição pedida em semana não publicada). Ficaram para o autor decidir as sugestões de tipos (`tuple`, `TipoRefeicao`, `@property`) e a consulta dupla da `FonteCardapio`, explicada no docstring de `_publicado`.
- TDD dos ajustes: três pares `test` → `fix`, com 18, 3 e 2 testes falhando antes de cada correção, conferidos commit a commit. Sabotagem das regras novas: 11 alterações, e todas derrubam ao menos um teste (na primeira rodada, o aviso de "refeição sem `FonteCardapio`" com a condição trocada por `True` sobreviveu; entrou um teste da refeição pedida sem nada no banco). As 23 sabotagens da primeira rodada continuam derrubando testes.
- Validação após os ajustes: `pytest` com 1330 testes aprovados e 1 ignorado, cobertura de `apps` de 98,34%; `ruff`, `bandit -lll`, `makemigrations --check` e `spectacular --validate --fail-on-warn` aprovados; o diagrama 4a renderiza no `mmdc`.
- Situação: ajustes da revisão aplicados; aguardando o recheck de AlvaroBento12 e o combinado com o front na #144 sobre como a tela vai saber quais dias e refeições existem na semana (seção 7 do guia).

## FE-06 — Deploy do M2 com BD e BE

- Issue: [#142](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/142). PR: [#215 — FE-06: build de produção sem o simulado e roteiro do deploy do M2](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/215).
- Ferramenta: Claude (Anthropic).
- Apoio: função `deveUsarSimulacao` no `apiClient` (regra do servidor simulado separada numa função, para ser testada), com o teste antes do código, e a seção "Deploy do M2 (FE-06)" no `docs/deploy/deploy-producao.md`, com a checagem antes de subir e o roteiro de ponta a ponta da BD-08 (#148). Os patches foram gerados pela IA e aplicados e commitados pela autora.
- TDD: o commit `test` (`f08b394`) vem antes do `feat` (`9c9f48f`); nele, os 5 casos de `deveUsarSimulacao` falhavam porque a função ainda não existia.
- Validação: `npm run test:ci` com 376 testes passando (cobertura de 90,27% de linhas / 81,41% de ramos), `npm run lint:ci` sem achados e `npm run build` sem erro, no PC da autora. O deploy e o roteiro em produção são feitos na VM pela equipe, e o resultado fica na #142 e na #148.
- Revisão humana: Álvaro Bento revisou o PR #215; os ajustes pedidos (passo 8 do roteiro, texto da garantia do build sem o simulado, link do PR e números nesta entrada) e as sugestões (passo do RI09, branch pelo nome, caso `'FALSE'` no teste, estilo da doc) foram aplicados.
- Situação: aguardando nova revisão.

## FE-07 — CampusView e rotas do campus

- Issue: [#143](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/143). PR: [#216 — FE-07: CampusView e rotas do campus](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/216).
- Ferramenta: Claude (Anthropic).
- Apoio: campus pelo `id` inteiro do `GET /api/campi/` (lista no `cardapioStore`, campus lembrado inteiro na `preferenciasStore`, com o nome antigo convertido no id), rotas `/`, `/campus` (`SeletorCampus`), `/campus/:campusId` (`CampusView`) e redirecionamentos de `/cardapio`, `/cardapio/:campusId` e `/fila`, `CardapioView` e `FilaView` como seções da `CampusView`, `AvisoExecutivo`, `RefeicaoEncerrada`, `CheckinBotao` com o campus da tela e a refeição selecionada, login levando à tela do campus (RF03.4) e servidor simulado com o `GET /campi/`. Os patches foram gerados pela IA e aplicados e commitados pela autora.
- TDD: o commit `test` (`ed37de6`: roteamento, tela com uma seção falhando, check-in com a refeição de quando o fluxo começou, stores) vem antes do `feat` (`e66b20a`). O `fix` `b1bdbb8` veio depois, com o teste junto: o redirecionamento sem campus levava o `campusId` e o vue-router avisava `Discarded invalid param(s)`.
- Revisão humana: Álvaro Bento revisou o PR #216. Ajustes aplicados, com os testes antes do código:
  - o `CheckinBotao` descarta o fluxo ao sair da tela, e o POST não sai quando a refeição encerra durante o GPS;
  - "Fila" rola até a seção também com a tela já aberta;
  - `/cardapio/<nome antigo>` abre aquele campus (e outro valor cai no 404), e a preferência antiga vira o id;
  - falha no `GET /api/campi/` aparece no cabeçalho com "Tentar novamente", o `AvisoExecutivo` vai pelo id e o check-in espera a lista confirmar o campus;
  - o 404 do cardápio vira "Campus não encontrado", e o campus lembrado que saiu do banco é esquecido;
  - `carregandoCampi`, a resposta de `/campi/` validada, erro e carregamento do cardápio por campus e a hora da tela atualizada a cada 30 s;
  - testes do `SeletorCampus` e de `idDeCampusValido` (`'01'` passou a ser recusado), "Usar minha localização" no cabeçalho da tela do campus e o C4 atualizado.
- Validação: `npm run test:ci` com 477 testes passando (cobertura de 90,74% de linhas / 82,9% de ramos), `npm run lint:ci` sem achados e `npm run build` sem erro, no PC da autora.
- Situação: aguardando nova revisão.

## BD-11 — Retenção de 4 semanas no app fila

- Issue: [#163](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/163). PR: [#220 — feat(banco): retenção de 4 semanas no app fila (BD-11)](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/220).
- Ferramenta: Claude (Anthropic).
- Apoio: `RetencaoFilaService` (`desvincular_antigos` e `desvincular_conta`), `CheckinRepository.desvincular_antes_de` e `desvincular_conta`, comando `desvincular_registros_fila` com o `DesvincularRegistrosFilaJob`, testes em `backend/apps/fila/tests/test_retencao_fila.py` e nota da implementação no Nível 4 da Fila (4d).
- TDD: testes no commit `a90291b`, antes do código; a coleta falhava porque o serviço, o método do repositório e o comando ainda não existiam.
- Testes: registro de 5 semanas sem conta e sem hora; campus, tipo, data, faixa, tempo de espera e marcador de pontos mantidos; borda de 4 semanas (o dia-limite fica); contagem e segunda rodada sem efeito; dois check-ins da mesma refeição sem conta (UNIQUE com NULL); agregação da previsão (contagem e média de espera por campus, tipo, data e faixa) igual antes e depois; resposta de saída sem vínculo; prazo lido da `ParametrosFilaConfig`; exclusão de conta só nos registros dela; dia de Brasília no job; saída e log do comando só com a contagem.
- Validação local (SQLite): `pytest` com 1348 testes aprovados e 1 ignorado (específico do MySQL), cobertura de 98%; `ruff check` e `ruff format --check` sem achados.
- Fora deste PR: o agendamento diário no cron fica com a BD-07 (#147); a previsão (BE-15) ainda não existe, então o teste confere a agregação que ela usa, e não a `PrevisaoView`.
- Revisão humana: [revisão de AlvaroBento12](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/220#issuecomment-7068712623), sem bloqueio para o merge, com quatro ajustes e sugestões.
- Ajustes da revisão (TDD: testes em `6fcee7c`, antes do código):
  - os docstrings e o C4 (4d) dizem exatamente o que é anulado (a conta, `registrado_em` e `data_hora`) e registram os horários que ficam, sem conta (`pontos_concedidos_em` e os da pergunta e da resposta de saída), a confirmar pela equipe;
  - a justificativa do marcador de pontos passou a ser a gamificação (ADR 0011);
  - testes dos dois lados do `OR` do `_desvincular` (sem conta e com hora, pelo `SET_NULL`; com conta e sem hora), nas duas tabelas; a mutação que tira a hora do filtro faz dois deles falharem (conferido localmente);
  - teste de rollback entre as duas tabelas (falha sem o `transaction.atomic()`, conferido localmente), contagens do `desvincular_conta`, a pergunta de saída mantida e o dia anterior ao limite de Brasília;
  - a falha do job vai para o log (`logger.exception`) e é propagada;
  - parâmetro `limite` no repositório, docstrings sem descrever como existente o que ainda não existe, `int` no diagrama e a explicação do UNIQUE com a conta nula.
- Sugestão não aplicada: as contagens separadas por tabela no log. O contrato continua `int`, como no C4, e os testes conferem cada tabela.
- Validação local depois da revisão (SQLite): `pytest` com 1356 testes aprovados e 1 ignorado, cobertura de 98%; `ruff check` e `ruff format --check` sem achados.
- Situação: ajustes da revisão aplicados, aguardando o recheck.

## BE-12 — Leitor do PDF

- Issue: [#139](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/139). PR: [#218 — BE-12: leitor do PDF do cardápio](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/218).
- Ferramenta: Claude (Anthropic).
- Apoio: a partir do guia da BE-12 (21/11/2026) e dos arquivos baixados do RU nessa data (HTML da página e os 10 PDFs das semanas de 16/11 e 23/11), testes e implementação de: correção do cabeçalho com a data entre parênteses (caso 26), divisão dos ícones quase encostados pelo vale de tinta (caso 27, sem mudar o `DISTANCIA_MAX_ICONE`), barra no fim da linha (caso 28, achado nos PDFs de Planaltina e do Darcy); `FonteNaoEncontradaError`, `DownloadError` e leitura do PDF em memória; `FonteCardapioConfig`, `CardapioDownloader` (página lida uma vez por execução, `localizar_pdfs` pelo título do campus, só `h1`–`h6`, conferência do host, da pasta, do prefixo do arquivo e das datas do link; `baixar` com SHA-256), `CardapioRepository` (atualiza a `Refeicao`, troca só categorias e pratos; decisões P1 e P2), `AlertaEquipeService` (3 e-mails por dia, 6 h de intervalo, `EMAIL_EQUIPE`), `LeitorCardapioService` (transação por semana, SHA-256, `_conferir_datas`, `_semana_atrasada`, `zerar_contador`) e o comando `ler_cardapio`. Docs: C4 do Leitor (4a, 4b e 4c com as assinaturas do código, P1 e P2), casos 26 a 28 no teste do BE-04, nota P2 no N4 do banco, `EMAIL_EQUIPE` no `.env.example` e no guia de deploy. O código foi gerado pela IA; os commits foram aplicados pelo autor do PR.
- TDD: cada `feat`/`fix` veio depois de um commit `test` com os testes da etapa falhando (`ImportError` nas etapas de classe nova; 7, 4 e 2 testes falhando nas três correções do parser). A sequência foi conferida commit a commit: os arquivos de teste de cada commit `test` falham nele e passam no commit seguinte. Um par `test` → `fix` a mais veio da conferência final com a ADR 0014 (a página era pedida uma vez por campus, e não uma por execução). Dois commits `test` são só de caracterização e já passam ao entrar: o ponta a ponta com a BE-11 e a borda do prazo de segunda, 12h (este, escrito porque uma sabotagem sobreviveu).
- Fixtures: HTML real da página (`tests/fixtures/pagina_ru/`) e 4 dos 10 PDFs (Gama de 16/11 e 23/11, Fazenda de 16/11 e Planaltina de 23/11). As variações do HTML (blocos em outra ordem, título ausente ou repetido, link de outro campus, semana repetida, datas ilegíveis, host ou pasta errados) são geradas no teste. Os 10 PDFs foram lidos à mão antes e depois de cada correção do parser: só mudaram as páginas afetadas (o almoço de 16/11 dos 5 campi passou a sair com marcadores, com o mesmo texto; três molhos com barra no fim da linha viraram um prato só). Nos 13 PDFs, o pior acerto de ícone ficou em 19,6 (limite 35) e a menor razão entre o 2º e o 1º colocado, em 1,67 (mínimo 1,3).
- Sabotagem manual (módulo crítico): 39 alterações (mais a do cache da página, coberta pelo último par) nas regras novas, entre elas as duas do QA-10 ("associar o link pela posição do bloco" e "ignorar o ícone de um marcador"). Na primeira rodada, uma sobreviveu (o prazo de segunda, 12h, trocado de `>=` para `>`): entrou o teste da borda, e as 39 passaram a derrubar ao menos um teste.
- Validação local (SQLite, Python 3.13): `pytest` com 1475 testes aprovados e 1 ignorado (específico do MySQL; eram 1330 na `develop` em `94e0f25`), cobertura de `apps` (com branches) de 98,59%, 100% nos módulos novos do `leitor` e 97% no parser; `ruff check`, `ruff format --check`, `bandit -lll`, `makemigrations --check` e `pip-audit` aprovados. Os três diagramas do C4 do Leitor renderizam no `mmdc`. `semgrep` (sem acesso às regras daqui) e `testes-mysql` ficam com o CI.
- Checklist do Plano de Testes (3.10): toda asserção é sobre o resultado; os valores esperados saem da imagem das páginas dos PDFs, do HTML real, do RF06, das ADRs 0006 e 0014 e do guia; nenhum mock da própria unidade (só a rede, com o `SiteDoRUFalso`, o e-mail, o relógio, e falhas injetadas num colaborador: o `remover_ausentes` levantando `DatabaseError` no teste da transação e o `processar` levantando erro num campus no teste do comando).
- Dependências novas: `requests==2.34.2` e `beautifulsoup4==4.15.0` (trazem `urllib3`, `certifi`, `idna`, `charset-normalizer`, `soupsieve` e `typing-extensions`).
- Revisão humana: revisão de AlvaroBento12 no PR #218. Três correções obrigatórias: o comando sempre saía com código 0; um erro fora das cinco exceções do Leitor (ex.: `DataError` do MySQL estrito) não gerava alerta; um PDF sem páginas apagava a semana em silêncio. Seis pontos importantes: o limite de e-mails podia prender para sempre o "não publicado"; o `zerar_contador` apagava o `ultimo_envio_em`; o `_enviar` não capturava erro de configuração; um alerta cujo e-mail falhou nunca era reenviado; os alertas da página só em texto ficavam fora da transação; e o P1 apagava sem rastro, confiando nas datas do link. Também testes, documentação e sugestões.
- Ajustes da revisão:
  - O comando sai com código 1 (`CommandError`) quando um campus termina em erro inesperado, depois de processar todos, e grava um alerta para ele.
  - O serviço trata qualquer outra exceção por semana: desfaz a transação, alerta "erro inesperado" e segue para a próxima semana.
  - Um PDF sem refeições é `FormatoPDFInvalidoError`.
  - Os alertas são só gravados durante a execução (os da página só em texto, dentro da transação da semana). No fim, sai **um** e-mail por campus com todos os pendentes dos tipos que o limite deixa enviar. Para isso entrou o campo `ALERTA_LEITURA_CARDAPIO.email_enviado_em`, na migração `0005`.
  - O `zerar_contador` zera só a quantidade.
  - O envio captura qualquer exceção.
  - O tipo do alerta vem de `RefeicaoEstruturada.falha`.
  - O Downloader reprova link de mais de 7 dias ou sobreposto a outro. O P1 registra cada refeição apagada no log e alerta a equipe sobre a mantida por ter avaliação.
  - Sugestões feitas: `FontePDF` imutável e com datas garantidas, `ArquivoPDF` com o SHA-256 calculado do conteúdo, incremento do contador com `F()` e dependências opcionais no `LeitorCardapioService`.
  - Testes: fuso UTC (contador, prazo do "não publicado" e hora do e-mail), rollback de uma releitura, P1 no serviço (PKs e avaliação preservadas) e nos limites da semana, mesmo SHA-256 em URL nova e PDF de 0 páginas. A falha só em texto passou a ser simulada no ponto da associação (`apoio_leitor.falhar_associacao_na_refeicao`), e as trocas no HTML passaram a ser feitas pelo href do link (`trocar_texto_do_link`), sem depender da ordem dos blocos.
  - Documentação: C4 do Leitor, N4 do banco, teste do BE-04, deploy e `.env.example`.
- Ficaram para outro PR (sugestões): download com `stream=True` e teto de tamanho, as exceções do Downloader num `leitor/erros.py` e um `assert` de transação aberta no `CardapioRepository`.
- TDD dos ajustes: quatro pares `test` → `fix`, com 5, 8, 31 e 8 testes falhando antes de cada correção, conferidos commit a commit. Três commits `test` são de caracterização e passam ao entrar: o relógio em UTC, a sobreposição de um dia só e a semana vigente no domingo à noite em UTC. Os dois últimos foram escritos porque duas sabotagens sobreviveram.
- Sabotagem dos ajustes: 30 alterações novas, entre elas as cinco que a revisão apontou como invisíveis à suíte. Na primeira rodada sobreviveram duas (`timezone.localtime` trocado por `agora` no cálculo da segunda-feira vigente, e a sobreposição estrita); entraram os testes, e as 30 derrubam ao menos um teste. As 39 da primeira entrega continuam derrubando (7 delas reescritas para o código novo).
- Validação após os ajustes: `pytest` com 1514 testes aprovados e 1 ignorado, cobertura de `apps` de 98,63% (100% nos módulos novos do `leitor`, 98% no parser); `ruff check`, `ruff format --check`, `bandit -lll` e `makemigrations --check` aprovados; os três diagramas do C4 do Leitor renderizam no `mmdc`.
- Segunda revisão de AlvaroBento12. Três pontos ainda impediam o merge:
  - (A) erro inesperado capturado nas semanas voltava a sair com código 0;
  - (B) `send_mail` que devolve 0 (com `EMAIL_EQUIPE=` vazio) contava como enviado;
  - (C) o corpo do PR estava duplicado em HTML.
- Ajustes da segunda revisão:
  - O `ResultadoLeitura` ganhou `inesperados` e `email_falhou`, e o comando sai com código 1 nos dois casos, depois de processar todos os campi.
  - `enviar_pendentes` devolve `ResultadoEnvio(enviados, falhou)`.
  - `send_mail` diferente de 1 é falha, e o log traz o código SMTP.
  - `EMAIL_EQUIPE` vazio cai no padrão.
  - O alerta do erro inesperado no comando tem `try` e log separados para gravar e enviar, e usa o `AlertaEquipeService` do serviço.
  - O link reprovado por datas, 7 dias ou prefixo não reprova o link certo por sobreposição.
  - O e-mail lista os alertas mais antigos primeiro.
  - Os alertas de uma transação desfeita não entram no resumo.
  - `ParametrosLeitorConfig` passou a ser injetável.
  - A ADR 0006 e o C4 registram o máximo de 4 e-mails numa falha intermitente e que execuções simultâneas não são suportadas.
  - O corpo do PR foi refeito.
- TDD da segunda revisão: um par `test` → `fix`, com 38 testes falhando antes da correção e passando depois (conferido commit a commit), e um commit `test` a mais com dois testes que fecharam brechas achadas na sabotagem.
- Sabotagem da segunda revisão: 12 alterações novas. Na primeira rodada, uma sobreviveu (os alertas de uma transação desfeita contando no resumo), porque o teste derrubava a transação antes do alerta. O teste passou a derrubar a transação no último passo, e as 12 derrubam ao menos um teste.
- Validação após a segunda revisão: `pytest` com 1524 testes aprovados e 1 ignorado, cobertura de `apps` de 98,65% (100% nos módulos novos do `leitor`, 98% no parser); `ruff check`, `ruff format --check`, `bandit -lll` e `makemigrations --check` aprovados; os três diagramas do C4 do Leitor renderizam no `mmdc`.
- Situação: ajustes da segunda revisão aplicados; aguardando o recheck de AlvaroBento12. Para a dupla do banco: o campo novo `email_enviado_em` (migração `0005`) e a mudança do `zerar_contador` estão no N4.

## FE-08 — Seção do cardápio ligada à API

- Issue: [#144](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/144). PR: [#219 — FE-08: seção do cardápio ligada à API](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/219).
- Ferramenta: Claude (Anthropic).
- Apoio: `cardapioStore.carregarRefeicao` ligado ao `GET /api/cardapio/` com campus, dia, refeição, marcadores e dieta como parâmetros (ADR 0005) e cache por combinação, `avaliacoesStore.carregarResumoDoDia` (`GET /api/avaliacoes/resumo/`), `AbasSemana` e `SeletorRefeicao` com a nota média, `CardapioView` com os avisos de "não publicado", "nenhuma opção" e filtro de marcadores desativado, dietas e marcadores com os nomes do backend (com a conversão dos filtros salvos com os nomes antigos), filtro no cliente retirado e servidor simulado no contrato do `GET /cardapio/` e do resumo do dia. Os patches foram gerados pela IA e aplicados e commitados pela autora.
- Contrato da BE-11 (#214) conferido com os comentários da #144: o simulado também dá 400 para marcador desconhecido, item vazio, parâmetro fora da lista e data fora da faixa; o fim do horário entra na refeição (9h30 ainda é café); um dia sem serviço pedido sem refeição passa ao próximo dia com serviço, e a tela avisa "Sem refeições neste dia" mantendo a aba. Enquanto o resumo do dia (`GET /api/avaliacoes/resumo/`) não sai do 501, o `SeletorRefeicao` mostra café, almoço e jantar sem nota.
- TDD, em três pares, sempre com o `test` antes do código:
  - `4438b55` → `0c64c85`: filtros persistidos e mandados como parâmetros, estados vazios, dia sem serviço, contrato do simulado e stores.
  - `84386ee` → `06cd8b5`: sobre a FE-07 revisada (#216). Erro e carregamento do cardápio por pedido, e o campus inexistente (400 "Não existe campus com esse id.") virando "Campus não encontrado".
  - casos da revisão → `fix`: os ajustes listados abaixo.
- Revisão humana: Álvaro Bento revisou o PR #219. Ajustes aplicados:
  - o 501 do resumo do dia não mexe mais no erro da tela de Avaliações (situação do resumo por dia, 501 como "indisponível" e as outras falhas no console);
  - o dia sem serviço vem pelo campo `semServico`, proposto ao backend e já mandado pelo simulado;
  - a refeição que o dia não serve vem publicada e vazia, como no backend, e aparece como "Esta refeição não é servida neste dia";
  - respostas que dependem do relógio e "não publicado" valem 5 minutos no cache, e o mesmo pedido ao mesmo tempo sai uma vez só;
  - o código `campus_nao_encontrado` também é aceito, e um teste do backend fixa a frase do campus inexistente;
  - um 400 com filtros oferece "Limpar filtros";
  - a resposta do cardápio é validada e os marcadores migrados não se repetem;
  - o simulado recusa `" 1"`, `01` e datas que não existem, e responde 501 no resumo com `simulacao.definirResumoDoDiaDisponivel(false)`;
  - testes de resposta fora de ordem, "Tentar novamente", troca de campus e dietas antigas, o C4 e os comentários desatualizados.
  - Ficam com o backend o `semServico` e o código `campus_nao_encontrado` no `GET /api/cardapio/`.
- Validação: `npm run test:ci` com 557 testes passando (cobertura de 91,84% de linhas / 85,22% de ramos), `npm run lint:ci` sem achados e `npm run build` sem erro, no PC da autora.
- Situação: aguardando nova revisão.
