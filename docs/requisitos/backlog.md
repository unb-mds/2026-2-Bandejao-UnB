# Backlog da R2 — Bandejão (05/11 a 22/11/2026)

> **Objetivo:** implementação completa, com testes, até **domingo, 22/11**. Os usuários testam em 23 e 24/11, e a entrega é em **25/11**.
> **Base:** branch `docs/gestao-projeto`, commit `92d95eb` (04/11). Conferido contra: Documento de Visão, Documento de Requisitos, glossário, C4 Níveis 1 e 2, C4 Nível 3 e os seis Níveis 4 do backend, C4 Níveis 3 e 4 do banco, C4 Níveis 3 e 4 do front-end, ADRs 0001 a 0011 e o documento `ordem-implementacao-e-controle-documentacao-r2.md`.
> **Ordem:** dentro de cada frente, primeiro os itens **INEG/VINC** (obrigatórios), na ordem em que devem ser feitos; depois os **EXTRA**, na ordem de prioridade. Um extra só começa quando os obrigatórios da frente para aquele marco estiverem prontos.

---

## 1. Como usar este backlog

### 1.1 IDs e frentes

| Prefixo | Frente | Quem |
|---|---|---|
| `BD-` | Banco de dados, infraestrutura, deploy e as tarefas de dados do backend (retenção, exclusão de conta) | Pessoa do banco (com assinatura) |
| `BE-` | Backend (Django/DRF) | Pessoa do back (com assinatura) |
| `FE-` | Frontend (Vue 3 + Pinia) | Pessoa do front (com assinatura) |
| `QA-` | Revisão, testes de aceite, campo e coleta de dados | Quem não tem assinatura |
| `DOC-` | Documentação e decisões | Quem não tem assinatura |

Itens extras têm o sufixo `E` (`BE-E1`, `FE-E1`…). O número do extra segue a ordem do documento de prioridades (EXTRA 1 = espera estimada, EXTRA 2 = recuperação de senha etc.).

### 1.2 Tamanho

| Tam. | Esforço com agente de IA, incluindo testes e revisão |
|---|---|
| **P** | Até meio dia |
| **M** | 1 dia |
| **G** | 2 dias ou mais |

### 1.3 Labels sugeridas para as issues do GitHub

`frente:banco|back|front|qa|doc` · `classe:ineg|vinc|extra|fora` · `marco:m1|m2|m3|m4|final` · `semana:1|2|3|4` · mais as labels de épico que já existem (`epico:login|cardapio|fila|avaliacao|gamificacao|transversal`).

### 1.4 Definition of Done (todo item)

- [ ] PR pequeno para a `develop`, revisado por alguém de **outra frente** ou sem assinatura, com o CI verde.
- [ ] **TDD**: o teste entra num commit antes do código (vermelho → verde → refatorar), a partir do critério Dado/Quando/Então ou da regra de negócio.
- [ ] **Testes no mesmo PR, no back e no front**, conforme o Plano de Testes (`docs/qualidade/plano-de-testes.md`): unitários para regras de negócio; de integração (cliente de teste do DRF no back, store + `apiClient` + servidor simulado no front); de interface (contrato OpenAPI no back, componentes com `@vue/test-utils` no front); de segurança; de propriedades quando a regra vale para qualquer entrada; e os específicos do tema que o item tocar (horário simulado, localização, concorrência, privacidade, PDF real).
- [ ] **Portas de qualidade do RNF06 verdes no CI**, no back e no front: cobertura de linhas ≥ 70% e escore de mutação ≥ 50% nos módulos críticos, 0 achados críticos ou altos em SAST e nas dependências (ADR 0013).
- [ ] Testes gerados por IA passaram pelo checklist do Plano de Testes (3.10) na revisão, e o uso está registrado no `AI-USAGE.md`. Dependência nova tem o link do pacote oficial na descrição do PR.
- [ ] Contrato OpenAPI atualizado se algum endpoint mudou.
- [ ] Nada de matrícula/SIAPE ou e-mail em resposta pública ou log, com o teste automatizado da ADR 0008. Nenhuma coordenada gravada nem em log (RI09). As rotas de cadastro, login, recuperação, reenvio e check-in não registram o corpo da requisição.
- [ ] Valores do Anexo A lidos da configuração, nunca fixos no código.
- [ ] **Nomes iguais aos da arquitetura**: classes dos Níveis 4 do backend, tabelas e colunas do Nível 4 do banco, componentes, stores e rotas do C4 do front, termos do glossário.
- [ ] Se a implementação divergir do C4, o documento de arquitetura é atualizado no mesmo PR.

### 1.5 Arquivos de arquitetura que cada frente deve passar ao agente

| Frente | Arquivos |
|---|---|
| BD | `docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md`, `docs/arquitetura/C4-nivel-3-banco-de-dados-bandejao.md`, ADRs 0004, 0007, 0008, 0011 |
| BE | `docs/arquitetura/backend/c4-nivel-3-backend.md` e o Nível 4 do componente da tarefa (`c4-nivel-4-*.md`), o Nível 4 do banco, as ADRs citadas no item |
| FE | `docs/arquitetura/front-end/c4-niveis-3-4-frontend-bandejao.md`, o contrato OpenAPI, ADRs 0005, 0007, 0009 |
| Todas | `docs/qualidade/plano-de-testes.md` e ADR 0013 (tipos de teste, metas e TDD) |

---

## 2. Divergências entre os documentos (resolvidas em 05/11)

A conferência encontrou pontos em que **dois documentos diziam coisas diferentes**. Todos foram resolvidos seguindo as recomendações abaixo, e os documentos dos dois lados foram atualizados (DOC-01). A tabela fica como registro de onde estava cada contradição.

| # | Divergência | Decisão aplicada | Documentos atualizados |
|---|---|---|---|
| **X1** | Tabela `ContadorAlerta` (limite de 3 alertas por dia e intervalo de 6 h) existia no Leitor e na ADR 0006, mas não no C4 do banco. Os tipos de alerta tinham nomes diferentes | Nova tabela `CONTADOR_ALERTA` (campus, tipo, data, quantidade enviada, último envio; UNIQUE por campus, tipo e data). Os tipos são os da ADR 0006 em todo o sistema: `LEGENDA_INVALIDA`, `ASSOCIACAO_FALHOU`, `FALHA_LEITURA_PDF` no `TipoAlerta` e `legenda_invalida`, `associacao_falhou`, `falha_leitura_pdf` no banco. Cada falha também fica em `ALERTA_LEITURA_CARDAPIO` | C4 Nível 3 e Nível 4 do banco, Nível 4 do Leitor, ADR 0006 |
| **X2** | O Leitor e a Exposição usavam o campo `alergenosIndisponivel` em `Refeicao`; o banco usava `REFEICAO.status_leitura` | A coluna é `status_leitura` (`ok`, `alergenos_indisponiveis`, `leitura_falhou`). `alergenosIndisponivel()` é uma propriedade derivada do model, não coluna | Nível 4 do banco, Níveis 4 do Leitor e da Exposição |
| **X3** | Ocultar avaliação era operação de moderação (ADR 0004, RNF08), sem coluna no banco nem regra na Avaliação | Nova coluna `AVALIACAO.oculta` (Boolean, default falso). Avaliação oculta não aparece nos comentários nem entra na nota média, na quantidade e no histórico; continua gravada, com o vínculo com a conta | Nível 4 do banco, Nível 4 da Avaliação, ADR 0004 |
| **X4** | A ADR 0005 definia `GET /api/cardapio/` com parâmetros; o C4 do front desenhava `GET /api/cardapio/{campus}/{semana}/` | `GET /api/cardapio/?campus=&semana=&dia=&refeicao=&marcadores=&dieta=`, conforme a ADR 0005. O cache do `cardapioStore` é por campus, semana, dia, refeição e filtros | C4 do front, Nível 4 da Exposição (tabela de endpoints) |
| **X5** | A ADR 0007 dizia que `GET /api/sessao/` devolve só apelido e tipo; o Nível 4 do Cadastro e o C4 do front incluíam `avisoPrivacidadePendente`. A duração da sessão não estava no Anexo A | `GET /api/sessao/` devolve `{apelido, tipo, avisoPrivacidadePendente}`. Novo parâmetro "Duração da sessão" (14 dias, renovada a cada uso) no Anexo A | ADR 0007, Documento de Requisitos (Anexo A e referências) |
| **X6** | O C4 Níveis 1 e 2 dizia que a zeragem dos pontos do semestre "ainda está em decisão" | Sem rotina de zeragem: uma linha de `PONTOS_SEMESTRE_CAMPUS` por conta, campus e semestre, como no Nível 4 da Gamificação e no banco | C4 Níveis 1 e 2 |

Também ficam para o kickoff as decisões D1 a D5 do documento de prioridades. O **destinatário dos alertas do leitor**, que era ponto em aberto da ADR 0006, foi decidido em 05/11: `equipe@bandejaounb.com.br` (ADR 0012).

---

## 3. O que a arquitetura definiu e o backlog segue

1. **A `CampusView` (tela do campus) é a tela principal** e junta cardápio, avaliações, previsão e check-in. Por isso **RF20.3, RF20.4 e RF03.4 são obrigatórios**. Só a **detecção de campus por GPS** (RF20.1, a troca automática do RF20.2, `DeteccaoCampusService`, `CampusDetectadoAviso`, fluxo 4d) é EXTRA 3.
2. **O front já tem o MVP**, com Pinia, `apiClient`, servidor simulado e as telas de login, cadastro, confirmação, recuperação de senha e histórico. Boa parte do trabalho do front é ligar o que existe à API real.
3. **O backend recomeça.** Os apps da `main` (`core`, `status`, `avaliacoes`, `cardapio`) não seguem o C4 Nível 3.
4. **Quem confere a qualidade da leitura do GPS (RN03: tempo limite, precisão e idade) é o PWA**, antes de enviar o check-in (fluxo 4a do front). O backend confere horário, duplicidade e distância ao RU, nessa ordem (Nível 4 da Fila).
5. **A pontuação acontece na mesma transação da contribuição** (`PontuacaoService.registrarContribuicao`), chamada pela Fila e pela Avaliação. Se a pontuação falhar, a contribuição não é gravada.
6. **A Bandeja de Ouro está fora.** Por isso não entram `posicao_final`, `BandejaOuroResolver`, `DistintivoIndicador`, `PosicaoRanking`, o campo `distintivo` das respostas e o fechamento do semestre. O contrato OpenAPI já nasce sem o campo `distintivo`.
7. **Campos de extras no contrato** (`perguntaDevidaEm`, `esperaEstimadaMin`, `bonusSemana`, `centro`, `raioDeteccaoMetros`) só entram no contrato quando o extra correspondente for feito.

---

## 4. Marcos e semanas

| Semana | Período | Foco | Marco |
|---|---|---|---|
| **1** | Qui 05/11 – Ter 10/11 | Decisões, fundação, conta e check-in | **M1** sáb 07/11 · **decisão do leitor** dom 08/11 · **M2 check-in em produção** ter 10/11 |
| **2** | Qua 11/11 – Sáb 14/11 | Cardápio, filtros, leitor e avaliação | **M3** sáb 14/11 |
| **3** | Dom 15/11 – Qua 18/11 | Pontos, previsão, patente, ranking e PWA | **M4 obrigatórios completos** qua 18/11 |
| **4** | Qui 19/11 – Dom 22/11 | Extras, testes de ponta a ponta, correções | **Pronto para os usuários** dom 22/11 |
| — | Seg 23/11 – Ter 24/11 | Teste com usuários, só correções críticas, limpeza da documentação | — |
| — | Qua 25/11 | Entrega | — |

> **Feriado:** sexta, 20/11 (Consciência Negra). O RU provavelmente não abre, então não há coleta de check-ins nesse dia.

**Regra de corte:** se um marco atrasar, o que sai são os extras, de baixo para cima. O dia 22/11 não muda.

---

## 5. Banco de dados (BD)

### 5.1 Obrigatórios

| ID | Item | Req. / Arquitetura | Pronto quando (inclui testes) | Tam. | Prazo | Depende de |
|---|---|---|---|---|---|---|
| **BD-01** | Models e migrations **exatamente como no Nível 4 do banco**, já com as decisões X1 a X3: `USUARIO`, `TOKEN`, `CAMPUS`, `REFEICAO`, `CATEGORIA`, `PRATO`, `MARCADOR`, `PRATO_MARCADOR`, `ALERTA_LEITURA_CARDAPIO`, `CONTADOR_ALERTA` (X1), `AVALIACAO` (com `oculta`, X3), `CHECKIN`, `TENTATIVA_CHECKIN`, `PONTUACAO_USUARIO`, `PONTOS_SEMESTRE_CAMPUS` (**sem** `posicao_final`). Criar já `PERGUNTA_SAIDA` e `RESPOSTA_SAIDA` (EXTRA 1). Cada model no app do componente dono (C4 Nível 3) | Banco N4, ADR 0001, 0008, 0011 | Migrations rodam em SQLite e MySQL. Testes das constraints: UNIQUE de avaliação, de check-in confirmado (com `usuario_id` nulo), de pontos por semestre, de pergunta por check-in; `CHECK` da nota, do comentário e dos pontos ≥ 0; apelido normalizado sem acento e sem maiúsculas | G | Sex 06/11 | BE-01, DOC-01 |
| **BD-02** | Job do CI com **MySQL 8 `utf8mb4`**, isolamento **READ COMMITTED**, obrigatório em PRs que mexem em migrations (além dos testes em SQLite) | Banco N4 (estratégia de migração 4, 6, 9), TT-02 | PR de teste com migration roda os dois jobs | M | Sex 06/11 | BD-01 |
| **BD-03** | Fixtures: 5 campi (nome, `ru_latitude`, `ru_longitude`, `raio_confirmacao_metros`), 10 marcadores. *Data migration* que cria `PONTUACAO_USUARIO` com zero ponto para contas existentes | Banco N4 (item 12), RN09 | `loaddata` funciona do zero. Testes conferem 5 campi e 10 marcadores | P | Sáb 07/11 | BD-01 |
| **BD-04** | Configuração com **todos os parâmetros do Anexo A** em classes de configuração (`HorariosRefeicaoConfig`, `ParametrosFilaConfig`, `ParametrosGamificacaoConfig` com `datasTerminoSemestre`, `ParametrosSessaoConfig`, `AvisoPrivacidadeConfig.versaoAtual`), `USE_TZ = True`, `TIME_ZONE = "America/Sao_Paulo"` | Anexo A, ADR 0007, banco N4 (item 10) | Nenhum número do Anexo A fora da configuração. Teste lê os valores | P | Sáb 07/11 | BD-01 |
| **BD-05** | Escolher a hospedagem (**escolhida em 06/11: máquina virtual Linux da Azure, com o crédito da Azure for Students**, ADR 0012, no lugar da Hostinger escolhida em 05/11) e fazer o **deploy de produção** em `bandejaounb.com.br`: VM pequena com MySQL em container (sem serviços gerenciados), IP estático, NSG só com 22, 80 e 443, alerta de orçamento do crédito, Brevo por SMTP na porta 587, HTTPS, MySQL `utf8mb4` com READ COMMITTED, **PWA e API no mesmo domínio** (ADR 0007), segredos em variáveis de ambiente, conexão com o banco criptografada se a hospedagem oferecer (ADR 0008), usuário de banco da aplicação separado do usuário da equipe | SP-02, ADR 0007, 0008 | "Hello world" da API e do PWA em produção por HTTPS (**M1**) | G | Sáb 07/11 (M1) e completo até seg 09/11 | — |
| **BD-06** | Coordenadas e raio de confirmação dos RUs **validados em campo** com QA-02. Raio do Darcy Ribeiro sem o Executivo, com a justificativa registrada | SP-04, L05, RI08, Fila N4 | Fixture atualizada com os valores medidos | P | Seg 09/11 | BD-03, QA-02 |
| **BD-07** | **Cron do sistema operacional** chamando os comandos do Django: `ExclusaoCadastroPendenteJob`, `clearsessions`, `LerCardapioCommand` (de 3 em 3 horas, ADR 0014, quando o BE-12 estiver pronto) e `DesvincularRegistrosFilaJob` (quando o BD-11 estiver pronto). Documentado junto às instruções de deploy | ADR 0003, 0007, 0014, RF02.3, RNF07.3 | Tarefas rodando em produção, com log | M | Qua 11/11 | BD-05 |
| **BD-08** | Teste de ponta a ponta do **M2 em produção**, com BE e FE | MC-01 | Cadastro → e-mail → login → check-in no RU do Gama, em produção | P | **Ter 10/11** | BD-05, BE-09, FE-05 |
| **BD-09** | **Monitor de disponibilidade** das 7h às 19h30 nos dias de refeição, com relatório | RNF02, TT-09 | Monitor ativo e relatório parcial disponível | P | Qui 12/11 | BD-05 |
| **BD-10** | Conferir os **índices** do Nível 4 (`CHECKIN` por campus, tipo e data; `PONTOS_SEMESTRE_CAMPUS` por campus, semestre, pontos e `atualizado_em`) com dados de teste no MySQL | RNF01 | Consultas de previsão e ranking usam os índices (`EXPLAIN`) | P | Sáb 14/11 | BD-01 |
| **BD-11** | **Retenção de 4 semanas** no app `fila`: `RetencaoFilaService.desvincularAntigos` e `desvincularConta`, chamados pelo `DesvincularRegistrosFilaJob`. Anula `usuario_id` e apaga `registrado_em` e `data_hora`; mantém campus, tipo, data, faixa, tempo de espera e marcador de pontos | RNF07.3, Fila N4 (4d) | Teste com registros de 5 semanas: vínculo e hora retirados, previsão continua igual | M | Seg 16/11 | BD-07, BE-09 |
| **BD-12** | **Exclusão de conta** no app `cadastro`: `RemoverContaCommand`, numa transação, marca `status = removido` e `removido_em`, chama `PontuacaoService.apagarContadores` e `RetencaoFilaService.desvincularConta`, encerra as sessões | RNF07.4, RNF08, Cadastro N4 (4d) | Teste dos quatro efeitos. Avaliações aparecem como "usuário removido". Conta some do ranking na hora | M | Seg 16/11 | BD-11, BE-14 |
| **BD-13** | **Roteiro de moderação** (ocultar avaliação com `oculta`, suspender conta, matrícula contestada, exclusão, ajuste manual de pontos), testado no MySQL de produção. Lista nominal de quem tem acesso | RNF08, ADR 0004, 0008, TT-07, L14 | Roteiro em `docs/` e cada operação executada uma vez | P | Ter 17/11 | BD-12 |
| **BD-14** | **Teste de carga** do cardápio e da previsão. Meta do RNF01: 2.000 usuários, p95 ≤ 3 s | RNF01, TT-08 | Resultado registrado. Se não chegar à meta, avisar o DOC (o número da documentação muda) | M | Sex 20/11 | M4 |
| **BD-15** | **Backup** do banco de produção, com o mesmo acesso restrito do banco, antes do teste com usuários | ADR 0008 | Backup feito e restauração testada uma vez | P | Sáb 21/11 | BD-05 |
| **BD-16** | **Origem do cardápio por campus** (ADR 0014): colunas `rotulo_pagina_ru` e `prefixo_arquivo_pdf` em `CAMPUS`, com a fixture dos 5 campi, e tabela `FONTE_CARDAPIO` (uma linha por campus e semana: `semana_inicio`, `url`, `sha256`, `verificado_em`, `processado_em`, UNIQUE por campus e semana), com migration. A URL da página e o prazo de segunda às 12h entram na `FonteCardapioConfig`, como os demais parâmetros do Anexo A (BD-04) | ADR 0014, Banco N4, Leitor N4c | Migration aplicada no SQLite e no MySQL; fixture com os 5 rótulos e prefixos do Anexo A | P | Qui 12/11 | BD-01, BD-03 |

### 5.2 Extras (em ordem)

| ID | Item | Classe | Pronto quando | Tam. | Janela |
|---|---|---|---|---|---|
| **BD-E1** | Retenção cobrindo `RESPOSTA_SAIDA` (perde o vínculo pelo check-in) e conferência de `CHECKIN.tempo_espera_min` | EXTRA 1 | Teste de retenção incluindo as respostas | P | Com BE-E1 |
| **BD-E2** | `TOKEN` do tipo `redefinicao_senha` em uso | EXTRA 2 | Teste do limite de 3 por hora contado em `TOKEN` | P | 19/11 |
| **BD-E3** | `centro_latitude`, `centro_longitude` e `raio_deteccao_metros` na fixture, medidos em campo | EXTRA 3 | Fixture atualizada | P | 19/11 |
| **BD-E4** | `sequencia_atual` e `ultima_semana_completada` em uso | EXTRA 7 | Testes da sequência com BE-E6 | P | 21/11 |
| **BD-E5** | Quatro consultas SQL dos indicadores de adesão, documentadas | EXTRA 8 | Consultas rodam em produção | P | 21/11 |

> **Sugestão de carga:** depois do M2 (10/11), a frente de banco fica mais leve que a do back. Ela pode assumir o **leitor do PDF** (BE-04 e BE-12), que é a maior tarefa do back e quase não depende do resto da API.

---

## 6. Backend (BE)

### 6.1 Obrigatórios

| ID | Item | Req. / Arquitetura | Pronto quando (inclui testes) | Tam. | Prazo | Depende de |
|---|---|---|---|---|---|---|
| **BE-01** | Recriar a estrutura conforme o **C4 Nível 3 do backend**: apps `cadastro`, `cardapio` (com o módulo `leitor`), `avaliacao`, `fila`, `gamificacao`. Retirar os apps antigos (`core`, `status`, `avaliacoes`). `settings` com DRF, sessão do Django em cookie `HttpOnly`/`Secure`/`SameSite=Lax`, CSRF por cabeçalho, `python-decouple`. `pytest` + `pytest-django` configurados, com as ferramentas de teste num `requirements-dev.txt` | RNF06, ADR 0001, 0003, 0007, 0013, TT-01 | `manage.py check` sem erro. Um teste por app, escrito antes do app (TDD), passando com `pytest` na máquina (o CI vem no BE-02). Teste das flags do cookie de sessão e do CSRF | P | Qui 05/11 | — |
| **BE-02** | **CI do backend** no GitHub Actions (`backend-ci.yml`, Plano de Testes 5.1), feito em TDD: jobs `lint` (`ruff`), `testes` (`pytest` com cobertura e `--fail-under=70` nos módulos críticos), `contrato` (OpenAPI gerado igual ao do repositório, quando o BE-03 existir) e `seguranca` (`bandit`, Semgrep, `pip-audit`). Proteção da `develop` exigindo os jobs verdes | RNF04, RNF06, ADR 0013, TT-02 | CI roda em todo PR para a `develop` e para a `main`. Cada porta foi vista barrando um PR de prova (link na descrição) | M | Sáb 07/11 | BE-01 |
| **BE-03** | **Contrato OpenAPI v1**, junto com o FE (por exemplo, com `drf-spectacular`), com os endpoints e formatos dos Níveis 4 e a decisão X4. Formato de erro com `codigo`. **Sem** o campo `distintivo` e sem os campos de extras ainda não feitos | Todos os Níveis 4, TT-04 | Arquivo do contrato no repo, revisado pelo FE (**M1**) | M | Sáb 07/11 | DOC-01 |
| **BE-04** | **Teste do leitor do PDF** com o PDF real do Gama: escolher a biblioteca, extrair texto e categorias e obter a **posição dos ícones** (`MarcadorIconMatcher`). Lista de casos difíceis | SP-01, RF06, ADR 0003, Leitor N4 | Script extrai uma refeição com pratos e marcadores corretos. **Decisão em 08/11**: leitor ou plano B (Admin). Biblioteca registrada na ADR 0003 (DOC-05) | M | **Dom 08/11** | — |
| **BE-05** | **Cadastro** `POST /api/cadastro/`: `CadastroService`, `IdentificadorExtractor` (estratégia por `TipoUsuario`), `MatriculaValidator` (formato, prefixo dinâmico, sequência, em métodos separados), `SiapeValidator`, `EmailInstitucionalValidator`, `ApelidoResolver` (409 recuperável na colisão do apelido extraído), `SenhaValidator`, aceite do aviso gravando `versao_aviso_aceita`. Na mesma transação, `PontuacaoService.inicializarConta` | RF01, RN01, RN02, ADR 0002, Cadastro N4 (4a) | Testes de cada regra da RN01 e RN02, dos cenários Gherkin do RF01 e de que a mensagem não revela qual campo já existe | M | Sex 06/11 | BD-01 |
| **BE-06** | **Confirmação de e-mail** `POST /api/confirmar-email/{token}/` e **reenvio** `POST /api/reenviar-confirmacao/`: `ConfirmacaoEmailService`, token com hash SHA-256 e validade de 24 h, envio por SMTP. `ExclusaoCadastroPendenteJob` como comando do Django | RF02, RNF04, Cadastro N4 (4b) | Testes de token válido, expirado, usado, reenvio que renova o prazo e exclusão do pendente expirado. E-mail real chega em `@aluno.unb.br` (QA-01) | M | Sáb 07/11 | BE-05 |
| **BE-07** | **Sessão** `POST`, `GET` e `DELETE /api/sessao/` (`SessaoView`, `LoginService`, `TentativaLoginTracker`: 5 tentativas em 10 min, bloqueio de 10 min; mensagem genérica; conta pendente com convite a confirmar). `GET` devolve só `{apelido, tipo, avisoPrivacidadePendente}`. `POST /api/privacidade/aceite/` (204). Conta suspensa ou removida vira `is_active = False` | RF03.1–RF03.3, ADR 0007, RNF07.1, Cadastro N4 (4c, 4d) | Testes do bloqueio, da mensagem genérica, do logout, do aviso pendente e do teste da ADR 0008 na sessão | M | Dom 08/11 | BE-06 |
| **BE-08** | `GET /api/campi/` (`CampiView`) com id e nome, cabeçalhos de cache e `ETag`. O raio de confirmação do RU nunca é publicado | RF07.2, Exposição N4 (4b) | Teste de resposta pública e do 304 | P | Dom 08/11 | BD-03 |
| **BE-09** | **Check-in** `POST /api/checkins/` (`CheckinView`, `CheckinService`, `ConfirmacaoLocalizacaoService`, `DistanciaGeografica`, `LocalizacaoRUConfig`). Ordem: aviso de privacidade (403, não grava tentativa) → horário → duplicidade → distância ao RU. Toda tentativa grava `TentativaCheckin` com `motivo`. Confirmado grava `Checkin` com `faixa_inicio` (horário local) e chama a pontuação na **mesma transação**. `IntegrityError` vira `checkin_duplicado`. Respostas: 201 com `checkin` e `pontos`; 422 com `fora_do_horario`, `checkin_duplicado` ou `localizacao_nao_confirmada` | RF11, RF12, RI03, RI09, Fila N4 (4a) | Testes da distância (dentro, borda, fora, RU de outro campus), horário, repetido, duas requisições simultâneas, aviso pendente e de que nenhuma coordenada é gravada ou logada | G | Seg 09/11 | BE-07, BD-03 |
| **BE-10** | Deploy do M2 com BD e FE | MC-01 | BD-08 OK | P | **Ter 10/11** | BE-09 |
| **BE-11** | **Cardápio** `GET /api/cardapio/?campus=&semana=&dia=&refeicao=&marcadores=&dieta=` (`CardapioView`, `CardapioQueryService`, `RefeicaoRepository`, `HorarioRefeicaoResolver` com a RN05 da R2, incluindo o próximo dia com serviço, `SemanaCardapioResolver` só com a semana vigente, `FiltroDietaService` e depois `FiltroMarcadorService`). Resposta `CardapioFiltrado`: `status` (`PUBLICADO`/`NAO_PUBLICADO`), `refeicaoEncerrada`, `avisoSujeitoAAlteracao`, `alergenosIndisponivel`, `filtroMarcadorDesativado`, `semOpcaoCompativel`, `contemMarcadorSelecionado` | RF05, RF07, RF08, RF09, RN05, ADR 0005, Exposição N4 (4a) | Testes de cada critério do RF08 e RF09, da RN05 com horário simulado (incluindo domingo e refeição encerrada) e de cada serviço isolado | G | Qui 12/11 | BD-01 |
| **BE-12** | **Leitor do PDF** no módulo `leitor` (`LerCardapioCommand`, `LeitorCardapioService`, `CardapioDownloader` com `localizarPDFs` pelo nome do campus na página do RU, nunca pela ordem dos blocos, um PDF por semana, conferência do nome do arquivo e dos dias do PDF dentro do intervalo do link, e nova leitura só quando URL ou SHA-256 mudam (ADR 0014), `FonteCardapioConfig`, `CardapioPDFParser`, `LegendaValidator`, `MarcadorIconMatcher`, `CardapioEstruturador.separarPratos`, `CardapioRepository`, `AlertaEquipeService` com `ContadorAlerta`: 3 avisos por dia e 6 h de intervalo). Cinco exceções, como no Leitor N4: fonte não encontrada, download e formato do PDF inválido (mantêm o último válido), legenda inválida e associação falhou (publica em texto e marca sem marcadores). **Ou plano B**: cadastro pelo Django Admin | RF06, ADR 0003, 0006, 0014, Leitor N4 | Testes com os PDFs reais e o HTML real da página do RU como fixture (inclusive com os blocos em outra ordem), de `separarPratos`, de cada exceção e do limite de alertas. Rodando no cron (BD-07) | G | Sex 13/11 | BE-04, DOC-01, BD-16 |
| **BE-13** | **Avaliação** `POST /api/avaliacoes/` (upsert, `JanelaAvaliacaoValidator`, validadores de nota e comentário, pontuação na mesma transação, resposta com `pontos`), `GET /api/refeicoes/{refeicaoId}/avaliacoes/` e `GET /api/avaliacoes/resumo/?campus=&data=` (uma consulta agrupada). `AvaliacaoPublicaMapper` só com apelido, "usuário removido" quando a conta foi removida, ignora avaliações ocultas (X3) | RF15, RI01, RI10, RNF08, Avaliação N4 | Testes dos cenários do RF15, da edição sem pontos em dobro, da conta removida, da oculta e do teste da ADR 0008 | M | Sex 13/11 | BE-11, BD-01 |
| **BE-14** | **Pontuação** no app `gamificacao`: `PontuacaoService.registrarContribuicao` (`travarPorConta` com `select_for_update`, marcador `pontos_concedidos_em`, `PontuacaoPolicy` com 10 e 5 pontos, avaliação só com check-in na mesma refeição, **avaliação liberada no check-in posterior**, pontos do semestre do campus da refeição via `SemestreResolver`), `inicializarConta`, `apagarContadores`. Bloco `pontos` (`total`, `contribuicao`, `avaliacaoLiberada`) | RF24, RN09, RI11, ADR 0011, Gamificação N4 (4a) | Testes: uma vez só (inclusive duas requisições simultâneas), check-in rejeitado não pontua, avaliação antes e depois do check-in, campus errado não pontua, semestre sem data de término, pontos nas férias | M | Sáb 14/11 | BE-09, BE-13 |
| **BE-15** | **Previsão** `GET /api/fila/previsao/?campus=&refeicao=&data=` (`PrevisaoView`, os seis passos do Nível 4 da Fila com `ParametrosFilaConfig`): janela de 4 semanas no mesmo dia da semana, faixas de 15 min no horário local, suficiência de dias, média só nos **dias com dados** (faixa vazia nesses dias conta como zero), cortes 25/50/75%, **empate: todas as faixas são pico**, "dados insuficientes". Público, só agregados | RF13, RN06, ADR 0010, Fila N4 (4c) | Testes com dados montados: abaixo e no mínimo de dias, empate, faixa zerada, outro dia da semana não conta, fuso horário | M | Seg 16/11 | BE-09, BD-10 |
| **BE-16** | **Progresso** `GET /api/gamificacao/progresso/` (patente derivada dos pontos, pontos totais, quanto falta, adesão) e **adesão** `POST`/`DELETE /api/gamificacao/adesao/` (204) | RF26.1, RF26.2, RN11, RF27.1, Gamificação N4 (4b, 4c) | Testes de cada limiar de patente, de que a patente não regride e da adesão | P | Seg 16/11 | BE-14 |
| **BE-17** | **Ranking** `GET /api/ranking/{campusId}/`: calculado na consulta, só quem aderiu, conta ativa e ≥ 1 ponto no semestre, ordem pelos pontos e desempate por `atualizado_em`, até 10 linhas. `RankingPublicoMapper` com `{campusId, semestre, linhas: [{posicao, apelido, patente}]}`, **sem pontos e sem `distintivo`** | RF27.2, RN12, RI12, Gamificação N4 (4c) | Testes: quem não aderiu não aparece, suspenso e removido não aparecem, empate, nenhum ponto na resposta (teste da ADR 0008) | M | Ter 17/11 | BE-16 |
| **BE-18** | **Portas finais do backend** e contrato OpenAPI final: cobertura de linhas ≥ 70% e escore de mutação ≥ 50% em cadastro, leitor, cardápio, avaliação, fila e gamificação; 0 achados críticos ou altos em SAST e nas dependências | RNF06, ADR 0013, TT-04 | Relatórios do CI (cobertura, mutação na base inteira e SAST) dentro das metas, anexados à issue | M | Qui 19/11 | BE-19 |
| **BE-19** | **Mutação no CI do backend**: `mutmut` configurado nos módulos críticos, job `mutacao` incremental nos PRs que mexem neles (falha abaixo de 50%) e rodada semanal na base inteira | RNF06, ADR 0013 | Job vermelho num PR de prova com teste sem asserção, verde depois da correção | P | Qua 11/11 | BE-02 |

### 6.2 Extras (em ordem)

| ID | Item | Classe | Pronto quando | Tam. | Janela |
|---|---|---|---|---|---|
| **BE-E1** | **Pergunta de saída e espera estimada** (Fila N4, 4b e 4c): `PerguntaSaidaService` criando a pergunta na transação do check-in, `perguntaDevidaEm` na resposta, `GET /api/fila/pergunta-pendente/` (204 ou 200), `POST /api/fila/respostas-saida/`, `POST /api/fila/perguntas-saida/{id}/dispensa/`, repetição, expiração na consulta (410), `tempo_espera_min` (RN07), 15 pontos uma vez por pergunta, `EsperaEstimadaService` com mediana e `SuficienciaEsperaValidator` (`esperaEstimadaMin`) | EXTRA 1 | Testes dos exemplos do RF22.1, de cada resposta da RN07, da repetição e da expiração | G | **Com uma 4ª pessoa: 09–12/11.** Sem ela: 18–20/11 (sem tempo de coletar dados) |
| **BE-E2** | **Recuperação de senha** (`SolicitarRecuperacaoSenhaView`, `RedefinirSenhaView`, `RecuperacaoSenhaService`, `SolicitacaoRedefinicaoTracker`: 3 por hora, link de 1 h, encerra todas as sessões) | EXTRA 2 | Testes dos critérios do RF04 | M | 19/11 |
| **BE-E3** | `centro` e `raioDeteccaoMetros` em `GET /api/campi/` (`LocalizacaoCampusConfig`) | EXTRA 3 | Teste com os mesmos casos de distância do front | P | 19/11 |
| **BE-E4** | Semana seguinte no `SemanaCardapioResolver` | EXTRA 4 | Teste com dois PDFs lidos | P | 20/11 |
| **BE-E5** | **Histórico** `GET /api/historico/?campus=&data=&refeicao=` (`HistoricoService`, sem filtros, somente leitura) | EXTRA 5 | Testes dos critérios do RF16 | P | 20/11 |
| **BE-E6** | **Sequência** (`SequenciaService`: dias distintos na semana de segunda a domingo, bônus de 20 fora do ranking, quebra avaliada na consulta, semana neutra) e `bonusSemana` no bloco `pontos` | EXTRA 7 | Testes dos critérios do RF25 e da semana neutra | M | 21/11 |

---

## 7. Frontend (FE)

### 7.1 Obrigatórios

| ID | Item | Req. / Arquitetura | Pronto quando (inclui testes) | Tam. | Prazo | Depende de |
|---|---|---|---|---|---|---|
| **FE-01** | Trazer o código do MVP da `main` para a `develop`. `apiClient` com cookie (`credentials: 'same-origin'`), cabeçalho `X-CSRFToken` nas escritas, 401 que limpa o `authStore`, erro com `codigo`. Servidor simulado só em desenvolvimento e testes | ADR 0007, RNF04, front 3b | Testes do `apiClient`: CSRF nas escritas, 401, erro com `codigo` | M | Sex 06/11 | BE-03 |
| **FE-02** | **CI do front** no GitHub Actions (`frontend-ci.yml`, Plano de Testes 5.2), feito em TDD: `lint` (ESLint e Oxlint sem `--fix`, num script `lint:ci`, com a regra `vitest/expect-expect`), `testes` (`vitest run --coverage` com `@vitest/coverage-v8` e limite de 70% de linhas nos arquivos críticos), `build` e `seguranca` (Semgrep, `npm audit --audit-level=high`). Proteção da `develop` exigindo os jobs verdes | RNF04, RNF06, ADR 0013, TT-02 | CI roda em todo PR. Cada porta foi vista barrando um PR de prova (link na descrição) | M | Sáb 07/11 | — |
| **FE-03** | `authStore` sem token (`carregarSessao`, `GET`/`POST`/`DELETE /api/sessao/`, guarda só apelido, tipo e `avisoPrivacidadePendente`). `CadastroView` (409 de apelido com campo extra mantendo os outros campos, mensagem que não revela qual campo existe), `ConfirmarEmailView` (token na query string), `LoginView` com reenvio para conta pendente, login leva a `/campus/:campusId`. Nada do formulário salvo no aparelho | RF01, RF02, RF03.1, RF03.2, RF03.4, front 4b | Vitest do `authStore` e dos desfechos do fluxo 4b | M | Dom 08/11 | FE-01, BE-07 |
| **FE-04** | `AvisoLocalizacao` no `App` raiz: duas etapas, "Agora não" guardado no `localStorage`, "Usar minha localização", passo a passo quando o navegador bloqueou | RF19, front 3a.1 | Vitest das três situações | P | Dom 08/11 | — |
| **FE-05** | `CheckinBotao` + `AvisoPrivacidade` + `filaStore` (fluxo 4a): aviso antes do GPS (`POST /api/privacidade/aceite/`), `getCurrentPosition` com tempo limite de 5 s, **precisão mínima e idade máxima (RN03)**, coordenadas só no corpo do `POST /api/checkins/` e descartadas em todos os desfechos, mensagem por `codigo` (com o horário quando fora do horário) | RF11, RF12, RN03, RNF07.1, RI09, front 4a | Vitest de cada desfecho do 4a e de que a store não guarda coordenadas | M | Seg 09/11 | FE-03, FE-04, BE-09 |
| **FE-06** | Deploy do M2 com BD e BE | MC-01 | BD-08 OK | P | **Ter 10/11** | FE-05 |
| **FE-07** | **`CampusView`** (front 3a.2) no lugar de `CardapioView` e `FilaView`. Rotas da estratégia de roteamento: `/` resolve o campus (RN04 do MVP: escolha manual lembrada ou seletor), `/campus` (`SeletorCampus`), `/campus/:campusId`, redirecionamentos de `/cardapio/:campusId` e `/fila`. `SeletorCampus` como componente (sai de `views/CampusView.vue`), `AvisoExecutivo`, `RefeicaoEncerrada`, `ConviteLogin`. Seções carregam em paralelo e falham sozinhas | RF20.3, RF20.4, RF03.4, RN04, RN05, RI08, front 3a.2 | Vitest do roteamento e da tela com uma seção falhando | G | Qui 12/11 | FE-01, BE-11 |
| **FE-08** | Seção do cardápio: `cardapioStore` ligado ao `GET /api/cardapio/` (X4), `AbasSemana` (semana vigente), `SeletorRefeicao` com nota média (`GET /api/avaliacoes/resumo/`), `FiltroCardapio` mandando marcadores e dieta como parâmetros (ADR 0005), avisos fixos do filtro, "não publicado", filtro desativado. Filtros e campus lembrados pela `preferenciasStore` | RF05, RF07, RF08, RF09, ADR 0005 | Vitest dos filtros persistidos e dos estados vazios. Filtro no cliente retirado | M | Sex 13/11 | FE-07, BE-11 |
| **FE-09** | `AvaliacaoWidget` ligado à API (nota, comentário de até 500 caracteres, edição, motivo quando indisponível, média, quantidade, comentários com apelido e "usuário removido") e `ConviteLogin` citando os pontos | RF15, RF05, front 3a.2 | Vitest de criar, editar e dos motivos de indisponível | M | Sáb 14/11 | FE-08, BE-13 |
| **FE-10** | `gamificacaoStore` e `PontosAviso` no `App` raiz ("+N pontos" quando `pontos.total > 0`), recebendo o bloco `pontos` de `filaStore` e `avaliacoesStore` | RF24.2, front 3b | Vitest de que o aviso aparece só com `total > 0` | P | Sáb 14/11 | BE-14 |
| **FE-11** | `FilaPrevisao`: faixas de 15 min com nível, pico em destaque (**várias faixas se houver empate**), "dados insuficientes", sem login | RF13, RN06, front 3a.2 | Vitest com empate e com dados insuficientes | M | Seg 16/11 | FE-07, BE-15 |
| **FE-12** | `ProgressoView` (`/progresso`) simplificada: patente, pontos totais, quanto falta (ou "patente máxima"), `RankingAdesaoToggle` com o aviso de que apelido e patente ficam públicos (sem citar a Bandeja), `BotaoSair` (`DELETE /api/sessao/`). Ao mudar a adesão, recarrega progresso e ranking. Visitante vê o `ConviteLogin`. **Sem** `SequenciaSemana`, `PosicaoRanking` e `DistintivoIndicador` | RF26.1, RF26.2, RF27.1, RF03.3, front 3a.3 | Vitest de logado, visitante e mudança de adesão | M | Ter 17/11 | FE-10, BE-16 |
| **FE-13** | `RankingView` (`/ranking/:campusId`, pública): `SeletorCampus`, `LinhaRanking` (posição, apelido, patente, sem pontos), `RankingVazio` | RF27.2, RI12, front 3a.3 | Vitest da lista e do vazio | M | Ter 17/11 | BE-17 |
| **FE-14** | **PWA instalável**: manifest válido e service worker registrado (conferir o `pwa.js` que já existe) | RNF05, Visão 9.2 | Lighthouse marca como instalável. Instalado em Android e iPhone | P | Qua 18/11 | — |
| **FE-15** | **Canal de contato para reclamações** visível no app (já existe na `HomeView` do MVP: levar para a navegação ou para a tela do campus) | RNF08, Visão 9.1 | Link visível sem login | P | Qua 18/11 | FE-07 |
| **FE-16** | Qualidade: funcional a partir de 360 px, guia de estilo, até 3 toques até o cardápio na primeira visita, últimas duas versões de Chrome, Firefox, Edge e Safari | RF17, RNF03, RNF05 | Checklist preenchido com QA-07 | M | Sex 20/11 | M4 |
| **FE-17** | **Mutação no CI do front**: StrykerJS com `@stryker-mutator/vitest-runner` nos arquivos críticos, job `mutacao` incremental nos PRs que mexem neles (falha abaixo de 50%) e rodada semanal. `fast-check` instalado para os testes de propriedades | RNF06, ADR 0013 | Job vermelho num PR de prova com teste sem asserção, verde depois da correção | P | Qua 11/11 | FE-02 |
| **FE-18** | **Testes de ponta a ponta** com Playwright em `frontend/e2e/` e workflow `e2e.yml` (PWA, API e banco no `docker compose`, fixtures do BD-03). Um fluxo por marco: cadastro e login (M1), check-in com localização simulada (M2), cardápio com filtros e avaliação (M3), previsão, progresso e ranking (M4) | RNF06, ADR 0013, Plano de Testes 3.5 | Workflow obrigatório nos PRs para a `develop` a partir do M2, com os fluxos do marco verdes | M | Qua 11/11 (estrutura e M1/M2), um fluxo novo por marco até qua 18/11 | FE-06, BD-03 |
| **FE-19** | **Portas finais do frontend**: cobertura de linhas ≥ 70% e escore de mutação ≥ 50% nos arquivos críticos (`apiClient`, stores de auth, cardápio, avaliações, fila e gamificação, guardas do roteador); 0 achados críticos ou altos em SAST e nas dependências | RNF06, ADR 0013 | Relatórios do CI dentro das metas, anexados à issue | M | Qui 19/11 | FE-17 |

### 7.2 Extras (em ordem)

| ID | Item | Classe | Pronto quando | Tam. | Janela |
|---|---|---|---|---|---|
| **FE-E1** | `PerguntaSaidaPopup` no `App` raiz (fluxo 4c: consulta ao abrir, ao voltar ao primeiro plano, em `perguntaDevidaEm` e a cada 2–3 min com pergunta não expirada; cinco respostas; dispensa; 410 silencioso) e `EsperaEstimada` dentro de `FilaPrevisao`, com o texto de apoio da L12 | EXTRA 1 | Vitest das respostas, da repetição, da dispensa e do 410 | G | Junto com BE-E1 |
| **FE-E2** | Ligar `RecuperarSenhaView` e `RedefinirSenhaView` (já existem) à API | EXTRA 2 | Vitest dos desfechos | P | 19/11 |
| **FE-E3** | `DeteccaoCampusService` e `CampusDetectadoAviso` (fluxo 4d): `GET /api/campi/` com cópia no `localStorage`, RN03, coordenadas descartadas, RN04 da R2, nova detecção depois de 30 min parado | EXTRA 3 | Vitest da distância (mesmos casos do backend) e da hierarquia da RN04 | M | 19–20/11 |
| **FE-E4** | Aba da semana seguinte em `AbasSemana` | EXTRA 4 | Vitest com e sem a semana seguinte | P | 20/11 |
| **FE-E5** | Ligar a `AvaliacoesView` (já existe) ao `GET /api/historico/` | EXTRA 5 | Vitest da tela somente leitura | P | 20/11 |
| **FE-E6** | Ícones dos marcadores ao lado dos pratos, usando `PratoFiltrado.marcadores` | EXTRA 6 | Revisão de design | P | 21/11 |
| **FE-E7** | `SequenciaSemana` em "Meu progresso" e `PatenteIndicador` na tela do campus | EXTRA 7 | Vitest | P | 21/11 |

### 7.3 Fora da R2 (não implementar)

`DistintivoIndicador`, `PosicaoRanking`, o campo `distintivo`, menções à Bandeja de Ouro no `AvisoPrivacidade` e no `RankingAdesaoToggle`, o descarte dos comentários ao mudar a adesão (só existia por causa da Bandeja), nível agora (RF14), push (RF23).

---

## 8. Revisão, testes e campo (QA) — quem não tem assinatura

| ID | Item | Pronto quando | Prazo |
|---|---|---|---|
| **QA-01** | Criar uma conta de teste `@aluno.unb.br` e conferir se os e-mails do sistema chegam (e se caem no spam) | Resultado avisado ao BE e ao BD | Sáb 07/11 |
| **QA-02** | Medir coordenadas e raio dos RUs com pelo menos dois celulares (pelo menos o Gama) | Valores entregues ao BD-06 | Seg 09/11 |
| **QA-03** | **Revisão de PRs** todos os dias, conferindo DoD, testes (com o checklist de testes gerados por IA do Plano de Testes, 3.10, e uma sabotagem rápida em pelo menos um teste do PR), o commit do teste antes do código (TDD) e se os nomes batem com a arquitetura | Nenhum PR parado mais de um dia | Contínuo |
| **QA-04** | Teste de ponta a ponta do M2 em produção, em celular real, no RU | Fluxo completo funcionando | Ter 10/11 |
| **QA-05** | **Coleta de check-ins** no almoço, em horários variados, todo dia útil a partir de 10/11. Prioridade: terças 10, 17 e 24/11 e quartas 11 e 18/11 | Planilha com quem fez check-in em cada dia | 10/11 a 24/11 |
| **QA-06** | **Testes de aceite pelos cenários Dado/Quando/Então** dos requisitos, em produção, a cada marco | Lista de cenários aprovados e bugs abertos como issue | Sáb 14/11 (M3) e qua 18/11 (M4) |
| **QA-07** | Testes em Chrome, Firefox, Edge e Safari, desktop e celular, e em tela de 360 px | Checklist preenchido | 19–21/11 |
| **QA-08** | Roteiro do teste com usuários (tarefas, formulário de feedback) e recrutamento | Roteiro pronto e usuários confirmados para 23–24/11 | Sáb 21/11 |
| **QA-09** | **Regressão final** de todos os fluxos obrigatórios em produção | Nenhum bug grave aberto | **Dom 22/11** |
| **QA-10** | **Testes de sabotagem** em 100% dos módulos críticos do back e do front, feitos por quem não escreveu os testes do módulo, numa branch descartável (Plano de Testes 3.8) | Registro da seção 6 do Plano de Testes preenchido, com "Sim" em todas as linhas | Qui 19/11 a sáb 21/11 |
| **QA-11** | **Auditoria dos testes gerados por IA**: procurar testes vazios, tautológicos ou que simulam a própria unidade, usando o checklist 3.10 e os mutantes sobreviventes do relatório de mutação | Lista de testes corrigidos (issue) e registro no `AI-USAGE.md` | Sáb 14/11 (M3) e qua 18/11 (M4) |

---

## 9. Documentação e decisões (DOC)

| ID | Item | Prazo |
|---|---|---|
| **DOC-01** | ~~Decidir e registrar as divergências X1 a X6 (seção 2) e atualizar os documentos afetados~~ **Concluído em 05/11**: C4 do banco (X1, X2, X3), Níveis 4 do Leitor, da Exposição e da Avaliação (X1, X2, X3), ADRs 0004 e 0006 (X1, X3), C4 do front (X4), ADR 0007 e Anexo A (X5), C4 Níveis 1 e 2 (X6) | Qui 05/11 |
| **DOC-02** | Registrar as decisões do kickoff: mínimo de dias da previsão, seção de trabalhos futuros, regras de pontos sem a pergunta de saída, datas do semestre 2026.2, hospedagem, provedor de SMTP e **destinatário dos alertas do leitor** (ADR 0006) | Sex 06/11 |
| **DOC-03** | **Texto do aviso de privacidade da R2** (LGPD): dados coletados e finalidades, citando fila, localização, gamificação e ranking (sem a Bandeja). Define a `versaoAtual` | Sáb 07/11 |
| **DOC-04** | Corrigir os links do banco (menu, README, Nível 3 fora da pasta `banco-de-dados/`), apagar ou substituir o `CONTEXT.md` antigo da raiz, substituir o `docs/requisitos/backlog.md` por este backlog e criar as issues no GitHub | Sáb 07/11 |
| **DOC-05** | Nova ADR de hospedagem e de SMTP (atualizando a Visão 4.4 e 9.2 e o Serviço de E-mail dos Níveis 1 e 2). ADR 0003 com a biblioteca do leitor (ou o plano B) | Seg 09/11 |
| **DOC-06** | Em 18/11, fechar a lista do que entrou e do que não entrou | Qua 18/11 |
| **DOC-07** | PR de limpeza da documentação, seguindo a Parte 2 do documento de prioridades (retirar o que não entrou de Visão, Requisitos, glossário, C4 e ADRs; mudanças condicionais; README da R2) | Prep. 19–22/11, merge até ter 24/11 |
| **DOC-08** | Conferir que o código bate com a arquitetura (models com o banco, classes com os Níveis 4, componentes com o front) e atualizar o "estado atual do código" do C4 do front | Dom 22/11 |
| **DOC-09** | Merge da documentação na `develop` (que está em 29/09) e depois `develop` → `main` | Ter 24/11 |
| **DOC-10** | Aceitar a ADR 0013 e o Plano de Testes (metas do plano de ensino no RNF06, para back e front) e avisar as frentes da mudança na Definition of Done | Sex 06/11 |
| **DOC-11** | ~~Revisar a ADR 0012 e os documentos que citavam a Hostinger para a Azure for Students~~ **Concluído em 06/11**: ADR 0012, ADRs 0003, 0004, 0007 e 0008, C4 Níveis 1 e 2, Visão (4.3, 4.4 com os cuidados com a Azure, 6 e 9.2) e BD-05. Menu e README também ganharam as ADRs 0009 a 0013, o Nível 4 da Gamificação e os links corretos do banco (parte do DOC-04) | Sex 06/11 |

---

## 10. Visão por dia

| Dia | BD | BE | FE | QA / DOC |
|---|---|---|---|---|
| Qui 05/11 | Kickoff, BD-01 | Kickoff, BE-01, BE-02, BE-04 | Kickoff, FE-01 | Kickoff, DOC-01 (concluído), DOC-02 |
| Sex 06/11 | BD-01, BD-02, BD-05 | BE-02, BE-03, BE-05, BE-04 | FE-01, FE-02 | DOC-02, **DOC-10**, QA-01, QA-02 |
| Sáb 07/11 | BD-03, BD-04, BD-05 (**M1**) | BE-02, BE-06, BE-03 (**M1**) | FE-02, FE-03 | DOC-03, DOC-04 |
| Dom 08/11 | BD-05 | BE-07, BE-08, **decisão BE-04** | FE-03, FE-04 | QA-03 |
| Seg 09/11 | BD-06, BD-05 | BE-09 | FE-05 | QA-02, DOC-05 |
| Ter 10/11 | **BD-08 (M2)** | **BE-10 (M2)**, BE-11 | **FE-06 (M2)**, FE-07 | QA-04, **QA-05 começa** |
| Qua 11/11 | BD-07 | BE-11, BE-12, BE-19 | FE-07, FE-17, FE-18 | QA-05 (quarta #1) |
| Qui 12/11 | BD-09, BD-16 | BE-12, BE-13 | FE-07, FE-08 | QA-05 |
| Sex 13/11 | BD-10 | BE-13, BE-12 | FE-08 | QA-05 |
| Sáb 14/11 | BD-10 (**M3**) | BE-14 (**M3**) | FE-09, FE-10 (**M3**) | QA-06, QA-11 |
| Dom 15/11 | Folga ou atraso acumulado | BE-15 | FE-11 | — |
| Seg 16/11 | BD-11, BD-12 | BE-15, BE-16 | FE-11, FE-12 | QA-05 |
| Ter 17/11 | BD-13 | BE-17 | FE-12, FE-13 | QA-05 (terça #2) |
| Qua 18/11 | **M4** | **M4**, BE-E1 (se sem 4ª pessoa) | FE-14, FE-15 (**M4**) | QA-05 (quarta #2), QA-06, QA-11, DOC-06 |
| Qui 19/11 | BD-E2, BD-E3 | BE-18, BE-E2, BE-E3 | FE-16, FE-19, FE-E2, FE-E3 | QA-07, QA-10, DOC-07 |
| Sex 20/11 (feriado) | BD-14 | BE-E4, BE-E5 | FE-16, FE-E3, FE-E4, FE-E5 | QA-07, QA-10 |
| Sáb 21/11 | BD-15, BD-E4, BD-E5 | BE-E6, correções | FE-E6, FE-E7, correções | QA-07, QA-08, QA-10 |
| Dom 22/11 | Correções | Correções | Correções | **QA-09**, DOC-08 |
| Seg 23 – Ter 24/11 | Só correções críticas | Só correções críticas | Só correções críticas | Teste com usuários, QA-05 (terça #3), DOC-07, DOC-09 |

---

## 11. Se uma 4ª ou 5ª pessoa assinar

| Pessoa | Assume | A partir de |
|---|---|---|
| **4ª** | BE-E1, BD-E1 e FE-E1 (pergunta de saída e espera estimada), do banco à tela. Meta: no ar até 12/11, para os check-ins das semanas seguintes gerarem tempos de espera | 09/11 |
| **5ª** | BE-14, BE-16, BE-17, FE-10, FE-12 e FE-13 (pontos, progresso e ranking de ponta a ponta), depois BE-18 e QA-07 | 09/11 |

Nesse caso, cada pessoa nova trabalha em apps e pastas próprias (`fila` para a pergunta de saída, `gamificacao`), e as migrations continuam só com a frente de banco.
