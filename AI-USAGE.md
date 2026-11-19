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

## ADR 0015 — Permissões de agentes de IA

- PR: [#156 — ADR 0015: permissões de agentes de IA no repositório](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/156).
- Ferramenta: Claude (Anthropic).
- Apoio: commit da ADR 0015 e das linhas no `docs/_sidebar.md` e no `README.md`, abertura do PR e ajustes da revisão: decisão reescrita (sem commit ou push direto na `main` e na `develop`, merge por um integrante depois da revisão de alguém diferente de quem operou o agente, force-push incluído, branches de trabalho fora da regra), status de volta para "Proposta", data do PR com a da redação entre parênteses, Contexto apoiado na Definition of Done, argumento da alternativa alinhado à ADR 0013, referências trocadas pelas que tratam do tema e ponto em aberto sobre "Require approvals".
- TDD: não se aplica (só documentação).
- Validação: links do sidebar e do README conferidos; afirmações da ADR conferidas com a ADR 0013, o `backlog.md` §1.4, o `plano-de-testes.md` §3.10 e o README (Gitflow).
- Revisão humana: [revisão de eusojj](https://github.com/unb-mds/2026-2-Bandejao-UnB/pull/156#pullrequestreview-5967413548), com pedido de mudanças.
- Situação: ajustes da revisão aplicados; aguardando nova revisão. A decisão sobre "Require approvals" fica para a equipe.
