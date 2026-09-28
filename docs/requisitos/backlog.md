# Backlog — Bandejão

> Backlog do produto **Bandejão** (Grupo 6, MDS/FCTE/UnB, 2026), reescrito em 28/09/2026 a partir do Documento de Visão, do Documento de Requisitos de Software, do glossário (`CONTEXT.md`), dos diagramas C4 (Níveis 1 a 4) e das ADRs 0001 a 0008. Substitui integralmente o `backlog.md` anterior, que ainda descrevia fila por votação, login "validado por matrícula" e previsão estática (ver a correspondência na Seção 8).

## 1. Como ler este documento

### 1.1 Releases

| Release | Data | Conteúdo |
|---|---|---|
| **R1 — MVP (protótipo)** | 28/09/2026 | Protótipo **somente frontend**, com dados fixos em JSON: cardápio, filtros, avaliações de exemplo e campo demonstrativo de avaliação. Acompanha a documentação inicial (requisitos e arquitetura). Sem backend, sem login, sem PWA instalável. |
| **R2 — Produto completo** | 25/11/2026 | **Entrega final da disciplina.** Todo o site operando em produção: todos os requisitos funcionais (RF01 a RF18, **incluindo RF10 e RF14**), não funcionais (RNF01 a RNF08) e inversos (RI01 a RI10). |

Não há itens para depois da R2: tudo o que estava em "Backlog do produto" entrou na R2.

### 1.2 Identificadores

| Prefixo | Tipo | Exemplo |
|---|---|---|
| `PROT-xx` | Item do protótipo da R1 | PROT-01 |
| `US-RR.n` | História de usuário. **`RR` é o número do RF de origem**, e `n` numera as histórias em que o RF foi dividido. Assim, `US-01.3` é a 3ª história do RF01, e a matriz de rastreabilidade continua sendo lida direto pelo ID | US-06.2 |
| `US-RNFxx.n` | História que nasce de um requisito não funcional com trabalho próprio | US-RNF08.1 |
| `SP-xx` | Spike: decisão ou investigação com prazo, cuja saída é uma ADR ou um parâmetro definido | SP-01 |
| `TT-xx` | Tarefa técnica, sem valor direto ao usuário, mas que bloqueia histórias | TT-04 |
| `MC-xx` | Marco com data fixa | MC-01 |

### 1.3 Campos de cada item

- **Prioridade:** Alta (Essencial), Média (Importante) ou Baixa (Desejável), conforme o Documento de Requisitos. Como tudo está na R2, a prioridade indica a **ordem de sacrifício** caso o prazo aperte, e não mais a release.
- **Esforço:** herdado da Matriz de Impacto x Esforço (Documento de Visão, Seção 8) quando existe. Os itens novos ficam "a estimar" para o planning poker. Não há pontos de história.
- **Depende de:** itens que precisam estar prontos antes.
- **Critérios de aceite:** em Gherkin (Dado/Quando/Então), detalhados na R2. Na R1, só o comportamento da tela sobre dados fixos.
- **Labels sugeridas:** `epico:login|cardapio|fila|avaliacao|transversal`, `release:r1|r2`, `prioridade:alta|media|baixa`, `tipo:historia|spike|tecnica|marco`, `status:concluido`, `onda:0|1|2|3`.

### 1.4 Requisitos não funcionais e inversos

Os RNFs e RIs **não** ficam numa tabela à parte. Eles aparecem de duas formas:

1. na **Definition of Done** (Seção 2), que vale para todo item da R2;
2. como **critérios dentro das histórias** afetadas ou, quando exigem trabalho próprio, como item próprio (`US-RNFxx`, `TT-xx`).

---

## 2. Definition of Done (vale para todo item da R2)

Um item só é considerado pronto quando:

- [ ] O código foi revisado em Pull Request e o CI passou, com testes em SQLite **e** um job contra MySQL para qualquer mudança de migration (TT-02).
- [ ] A cobertura de testes dos módulos críticos (leitor de cardápio, cadastro/autenticação, avaliação, fila) é de pelo menos **60%** (RNF06).
- [ ] Senhas só são armazenadas como hash (RI04, RNF04); a comunicação usa HTTPS (RNF04); consultas usam o ORM do Django, nunca SQL concatenado; texto digitado pelo usuário é escapado na saída (XSS).
- [ ] Nenhuma resposta pública nem log expõe matrícula/SIAPE ou e-mail (RI10, ADR 0008).
- [ ] Nenhuma coordenada de localização é gravada no banco nem em log (RI09).
- [ ] A tela é funcional a partir de 360 px e segue o guia de estilo (RF17, RNF03).
- [ ] A tela funciona nas duas versões mais recentes de Chrome, Firefox, Edge e Safari, em desktop e celular (RNF05).
- [ ] Os valores do Anexo A (horários, limites, prazos, raios) são lidos da configuração, nunca fixados no código.
- [ ] O contrato OpenAPI (TT-04) foi atualizado se algum endpoint mudou.
- [ ] Textos de tela e nomes no código seguem o glossário (`CONTEXT.md`): **Marcador** (nunca "alérgeno"), **Refeição**, **Apelido**, **Usuário** etc.
- [ ] O documento de arquitetura afetado foi atualizado se a implementação divergiu do desenho.

---

## 3. R1 — MVP (protótipo) · 28/09/2026

Protótipo só de frontend (Vue 3 + Vite), para apresentar à professora uma ideia geral do site. Os dados de cardápio e de avaliações são **fixos em JSON**, lidos diretamente pelas Views, e as avaliações exibidas foram **criadas pela equipe como exemplo** (a professora será informada disso).

**Limitações conhecidas da R1**, todas tratadas na R2:

| Limitação | Tratada em |
|---|---|
| Não há backend: o cardápio não vem do PDF e as avaliações não são salvas | TT-01, US-06.x, US-15.x |
| As Views leem JSON diretamente, sem stores nem `apiClient` (diferente do C4 do frontend, Nível 3b) | TT-05 |
| Os filtros de marcador e de dieta rodam no cliente (a ADR 0005 manda filtrar no backend) | US-08.1, US-09.1 |
| Não há cadastro nem login | US-01.x a US-05.1 |
| O PWA não é instalável (sem manifest nem service worker) | US-RNF05.1 |

| ID | Item | Ref. | Status |
|---|---|---|---|
| PROT-01 | Cardápio por campus, dia e refeição, com categorias em lista hierarquizada e navegação por abas entre os dias | RF05, RF07 | Concluído |
| PROT-02 | Filtro de marcadores no cliente: pratos sinalizados com "Contém: …" | RF08 | Concluído |
| PROT-03 | Filtro de dieta no cliente (Sem filtro / Ovolactovegetariano / Vegetariano estrito) | RF09 | Concluído |
| PROT-04 | Avaliações de exemplo exibidas junto à refeição (nota média, quantidade e comentários com apelido) | RF15 | Concluído |
| PROT-05 | Campo demonstrativo de avaliação (estrelas + comentário), sem persistência | RF15 | Concluído |
| PROT-06 | Identidade visual: paleta, tipografia e espaçamento aplicados às telas do protótipo | RF17 | Concluído |
| DOC-01 | Documentação inicial: Documento de Visão, Documento de Requisitos, glossário, C4 Níveis 1 a 4 e ADRs 0001 a 0008 | — | Entregue em 28/09 (ver `correcoes-documentos.md`, parte A) |

**Labels:** `release:r1`, `status:concluido`, mais a label do épico.

---

## 4. R2 — Produto completo · 25/11/2026

### 4.1 Ordem sugerida (ondas)

Não é alocação em sprints, que depende do planning poker. É a ordem imposta pelas dependências e pelo marco do check-in.

| Onda | Período sugerido | Foco | Itens |
|---|---|---|---|
| **0 — Fundação** | 29/09 a 10/10 | Tirar as incertezas técnicas e montar a base | SP-01, SP-02, SP-03, SP-04, TT-01, TT-02, TT-03, TT-04, TT-05 |
| **1 — Núcleo** | 13/10 a 24/10 | Cardápio real e conta de usuário, já em produção | TT-06, US-06.1 a US-06.5, US-07.1, US-08.1, US-09.1, US-01.1 a US-01.5, US-02.1 a US-02.3, US-03.1 a US-03.3, US-05.1 |
| **2 — Check-in e avaliação** | 27/10 a **03/11** | Check-in em produção a tempo de gerar dado para a previsão | US-11.1, US-12.1, **MC-01**, US-15.1, US-15.2, US-RNF08.1, US-04.1, US-04.2 |
| **3 — Completar o produto** | 04/11 a 20/11 | Previsão, histórico e o restante | MC-02, SP-05, US-13.1, US-14.1, US-16.1, US-18.1, US-10.1, US-RNF05.1, US-RNF07.1, US-RNF08.2, US-17.1, TT-07, TT-08, TT-09 |
| **Congelamento** | 21/11 a 24/11 | Só correção de defeitos e ensaio da apresentação | — |

**Caminho crítico:** SP-01 (PDF) → US-06.x (leitor) → US-07.1 (cardápio real). Em paralelo, SP-02 (hospedagem) → TT-06 (deploy) → US-03.1 (login) → US-11.1/US-12.1 (check-in) → **MC-01 (03/11)** → MC-02 (coleta) → US-13.1 (previsão exibindo dados em 25/11).

---

### 4.2 Spikes

#### SP-01 — Biblioteca de leitura do PDF com o PDF real do Gama

**Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 0 | **Prazo:** 10/10
**Labels:** `tipo:spike`, `epico:cardapio`, `release:r2`, `prioridade:alta`

**Objetivo:** escolher a biblioteca Python de leitura de PDF e comprovar que dá para (a) extrair o texto das categorias e pratos e (b) obter a posição dos ícones de marcador, para associá-los aos pratos (RF06, L03). Decidir se o leitor continua como módulo do backend ou precisa virar container separado (ADR 0003).

**Saída esperada:**
- Script de teste que extrai 1 página (1 refeição) do PDF do Gama de 21/9 a 27/9 com pratos e marcadores corretos.
- ADR 0003 atualizada com a biblioteca escolhida.
- Lista de casos difíceis encontrados, que viram casos de teste de US-06.2 e US-06.3.

**Bloqueia:** US-06.1 a US-06.5.

#### SP-02 — Hospedagem e frequência do cron

**Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 0 | **Prazo:** 10/10
**Labels:** `tipo:spike`, `epico:transversal`, `release:r2`, `prioridade:alta`

**Objetivo:** escolher a hospedagem de produção que atenda a:
- Python/Django e MySQL (ADR 0001);
- HTTPS;
- **tarefas agendadas** (cron do leitor, ADR 0003, e job de expiração de cadastro pendente, US-02.3);
- **PWA e API no mesmo domínio**, exigido pelo cookie de sessão (ADR 0007);
- custo compatível com manter o sistema no ar depois da disciplina (Visão 4.4).

**Saída esperada:**
- Nova ADR de hospedagem.
- Frequência do cron definida com margem para a meta de 24 h do RF06 (sugestão: a cada 6 h).
- Responsáveis e custo pós-disciplina registrados na Visão 4.4.

**Bloqueia:** TT-06, e por consequência todo item que precisa estar em produção.

#### SP-03 — Provedor de e-mail e destinatário dos alertas

**Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 0 | **Prazo:** 10/10
**Labels:** `tipo:spike`, `epico:login`, `release:r2`, `prioridade:alta`

**Objetivo:** escolher o provedor SMTP (C4 Nível 2) e testar a entrega em caixas `@aluno.unb.br` e `@unb.br`, verificando se as mensagens caem em spam. Definir o endereço que recebe os alertas do leitor (ADR 0006, ponto em aberto).

**Saída esperada:** ADR 0006 atualizada e credenciais de SMTP configuradas como variável de ambiente.

**Bloqueia:** US-02.1, US-02.2, US-04.1, US-06.5.

#### SP-04 — Coordenadas e raio de cada RU

**Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 0 | **Prazo:** 24/10
**Labels:** `tipo:spike`, `epico:fila`, `release:r2`, `prioridade:alta`

**Objetivo:** definir latitude, longitude e raio de confirmação dos 5 RUs (Anexo A), garantindo que o raio do Darcy Ribeiro **exclua o Restaurante Executivo** (RI08). Testar no local com pelo menos dois celulares diferentes, porque a precisão do GPS em ambiente fechado varia.

**Saída esperada:** valores gravados na fixture de Campus (TT-03), com a justificativa do raio do Darcy Ribeiro registrada no Anexo A.

**Bloqueia:** US-12.1.

#### SP-05 — Janela e limiares do Nível agora

**Prioridade:** Baixa | **Esforço:** a estimar | **Onda:** 3 | **Prazo:** 11/11
**Labels:** `tipo:spike`, `epico:fila`, `release:r2`, `prioridade:baixa`

**Objetivo:** definir a janela de check-ins recentes e os limiares dos quatro níveis do RF14, levando em conta o risco de mostrar "vazia" por baixa adesão (L08). Usar os check-ins reais coletados em MC-02 para calibrar.

**Saída esperada:** critérios de aceite do RF14 completados no Documento de Requisitos e novos parâmetros no Anexo A.

**Bloqueia:** US-14.1.

---

### 4.3 Tarefas técnicas

| ID | Tarefa | Onda | Depende de | Bloqueia |
|---|---|---|---|---|
| **TT-01** | Estruturar o backend Django/DRF com um app por recurso (`cadastro`, `cardapio` com o módulo `leitor`, `avaliacao`, `fila`), cada um com models, serializers, views e URLs próprios (RNF06, ADR 0001, ADR 0003) | 0 | — | todas as US de backend |
| **TT-02** | CI no GitHub Actions: testes e cobertura em SQLite a cada PR e um job com serviço MySQL 8 (`utf8mb4`) obrigatório para PRs com migration (C4 Banco, estratégia de migração, itens 6 e 7) | 0 | TT-01 | DoD |
| **TT-03** | Fixtures e configuração: 5 Campus, 10 Marcador; parâmetros do Anexo A (horários, prazos, limites, faixas, cortes, fuso `America/Sao_Paulo`) centralizados em configuração | 0 | TT-01 | US-06.x, US-07.1, US-11.1, US-13.1, US-15.1 |
| **TT-04** | Contrato da API em OpenAPI, combinado entre as duplas de frontend e backend. Inclui `GET /api/cardapio/` com parâmetros de query (ADR 0005), `POST /api/confirmar-email/` com token no corpo, as rotas de sessão (ADR 0007) e o formato de erro padrão | 0 | — | TT-05 e todas as US com endpoint |
| **TT-05** | Frontend: adotar Pinia, criar as stores (`authStore`, `preferenciasStore`, `cardapioStore`, `avaliacoesStore`, `filaStore`) e o `apiClient` (C4 do frontend, Nível 3b). Tirar a leitura de JSON das Views e o código de filtro do cliente | 0–1 | TT-04 | todas as US de frontend da R2 |
| **TT-06** | Deploy de produção: HTTPS, MySQL `utf8mb4`, PWA e API no mesmo domínio, cron do leitor e do job de expiração configurados e **documentados junto às instruções de deploy** (ADR 0003), variáveis de ambiente para segredos | 1 | SP-02, TT-01 | MC-01 e toda entrega em produção |
| **TT-07** | Roteiro de moderação (ADR 0004): documentar as operações manuais permitidas no banco (ocultar avaliação, suspender conta, tratar matrícula contestada, excluir conta com avaliações anônimas), quem da equipe tem acesso e como executar cada uma. Testar no MySQL de produção | 3 | US-RNF08.1 | — |
| **TT-08** | Teste de carga: 2.000 usuários simultâneos consultando o cardápio (e a previsão), com p95 ≤ 3 s medido no servidor (RNF01). Registrar o resultado e os ajustes feitos (índices, cache) | 3 | US-07.1, US-13.1 | — |
| **TT-09** | Monitor de disponibilidade: verificação externa periódica das 7h às 19h30 nos dias de refeição, com relatório de disponibilidade até a entrega (RNF02) | 3 | TT-06 | — |

---

### 4.4 Marcos

#### MC-01 — Check-in em produção até 03/11

**Labels:** `tipo:marco`, `epico:fila`, `release:r2`

Em 03/11/2026, um usuário real consegue, em produção, se cadastrar, confirmar o e-mail, fazer login e fazer check-in confirmado por GPS no RU do Gama.

**Motivo:** 25/11 é uma quarta-feira. A previsão (RF13) compara o mesmo dia da semana e só aparece com check-ins em **3 dias distintos** na janela de 4 semanas. Para haver previsão na apresentação, é preciso ter check-ins nas quartas **04/11, 11/11 e 18/11**.

**Depende de:** TT-06, US-01.x, US-02.1, US-03.1, US-11.1, US-12.1, SP-04.

#### MC-02 — Coleta de check-ins pela equipe

**Labels:** `tipo:marco`, `epico:fila`, `release:r2`

A equipe (e colegas convidados) faz check-in no RU nas quartas 04/11, 11/11 e 18/11, no almoço, em horários variados, para garantir o mínimo de dados da previsão da apresentação. Registrar na apresentação que os dados vêm desse uso real.

---

### 4.5 Épico 1 — Login

#### US-01.1 — Cadastro em duas etapas

**Ref.:** RF01, RNF07 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz, item 5.1) | **Onda:** 1
**Depende de:** TT-01, TT-05 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como pessoa da Comunidade da UnB, quero me cadastrar escolhendo primeiro se sou Estudante, Professor ou Servidor, para ver só os campos que se aplicam a mim.

**Critérios de aceite:**
- Dado que abro o cadastro, quando escolho "Estudante", então vejo os campos e-mail institucional, apelido e senha.
- Dado que abro o cadastro, quando escolho "Professor" ou "Servidor", então vejo os campos SIAPE/matrícula funcional, e-mail institucional e senha, e as duas opções levam ao mesmo fluxo.
- Dado que informo uma senha com menos de 8 caracteres, quando envio, então o cadastro é rejeitado com a regra da senha.
- Dado que não marquei a ciência do aviso de privacidade (dados coletados e para quê), quando envio, então o cadastro não é concluído.
- Dado que o cadastro foi aceito, quando a conta é criada, então ela fica **pendente** até a confirmação do e-mail e vejo "verifique seu e-mail", com a opção de reenviar.
- Dado que preenchi o formulário, quando saio da tela, então nenhum campo (inclusive a senha) fica salvo no aparelho.

#### US-01.2 — Cadastro de Estudante

**Ref.:** RF01, ADR 0002 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 1
**Depende de:** US-01.1, US-01.3 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Estudante, quero me cadastrar só com o e-mail institucional, o apelido e a senha, sem digitar a matrícula à parte.

**Critérios de aceite:**
- Dado que informo `251098732@aluno.unb.br`, quando envio, então o sistema extrai a matrícula `251098732` e a valida (US-01.3).
- Dado que informo um e-mail fora do formato `matricula@aluno.unb.br` (outro domínio, letras antes do "@"), quando envio, então o cadastro é rejeitado com mensagem específica de formato.
- Dado que digito um apelido com 3 a 20 caracteres e sem espaços, quando envio, então ele é aceito (sujeito à unicidade, US-01.5).
- Dado que digito um apelido com menos de 3 ou mais de 20 caracteres, ou com espaço, quando envio, então o cadastro é rejeitado com a regra do apelido.

#### US-01.3 — Validação de formato da matrícula de Estudante

**Ref.:** RF01, L10, Anexo A | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** TT-03 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como equipe, quero rejeitar matrículas com formato impossível, para reduzir cadastros com matrícula inventada (L01).

**Critérios de aceite:**
- Dado uma matrícula com 8 dígitos, quando validada, então é rejeitada (L10).
- Dado uma matrícula com letras, pontuação ou quantidade de dígitos diferente de 9, quando validada, então é rejeitada.
- Dado que o semestre corrente é 2026/2, quando os 3 primeiros dígitos são `101`, `152` ou `262`, então o prefixo é aceito; quando são `092`, `263`, `271` ou `253` (3º dígito diferente de 1 e 2), então é rejeitado.
- Dado que o semestre corrente muda, quando o sistema recalcula o intervalo, então o novo código do semestre passa a ser aceito sem alteração de código (o parâmetro vem da data do sistema, Anexo A).
- Dado que os 6 dígitos finais são `123456`, `654321` ou `111111`, quando validada, então é rejeitada.
- Cada uma das três regras tem testes unitários próprios (`MatriculaValidator`, C4 N4 Cadastro).

#### US-01.4 — Cadastro de Professor/Servidor

**Ref.:** RF01, ADR 0002 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 1
**Depende de:** US-01.1 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Professor ou Servidor, quero me cadastrar com SIAPE, e-mail `@unb.br` e senha, com o apelido gerado automaticamente a partir do e-mail.

**Critérios de aceite:**
- Dado um SIAPE com exatamente 7 dígitos numéricos, quando envio, então é aceito; com outro formato, é rejeitado com mensagem específica.
- Dado um e-mail fora do domínio `@unb.br`, quando envio, então é rejeitado.
- Dado o e-mail `maria.silva@unb.br`, quando o cadastro é processado, então o apelido gerado é `mariasilva` (caracteres não alfanuméricos removidos).
- Dado que o apelido gerado já está em uso ou fica fora de 3 a 20 caracteres, quando envio, então o formulário **reaparece com os demais campos preenchidos** e um campo extra pedindo um apelido digitado manualmente.

#### US-01.5 — Unicidade de matrícula/SIAPE, e-mail e apelido

**Ref.:** RF01, L01 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-01.2, US-01.4 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Usuário, quero que minha matrícula/SIAPE e meu apelido pertençam só à minha conta.

**Critérios de aceite:**
- Dado que a matrícula/SIAPE ou o e-mail já pertence a outra conta, confirmada **ou pendente**, quando envio, então o cadastro é rejeitado com a mensagem combinada **"matrícula/SIAPE ou e-mail já cadastrado"**, sem dizer qual dos dois, e com um link para o canal de contato (US-RNF08.2), para quem quiser contestar.
- Dado que existe o apelido `Ana`, quando alguém tenta `ana` ou `ANA`, então é rejeitado (unicidade sem distinção de maiúsculas e minúsculas, via `apelido_normalizado`, igual em SQLite e MySQL).
- Dado que duas requisições simultâneas tentam a mesma matrícula, quando ambas chegam ao banco, então só uma é criada (restrição UNIQUE no banco).
- Dado uma conta criada, quando qualquer endpoint é chamado, então não existe forma de alterar o apelido.

#### US-02.1 — Confirmação de e-mail

**Ref.:** RF02, RNF04 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-01.1, SP-03 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como pessoa recém-cadastrada, quero confirmar meu e-mail por um link, para ativar minha conta e garantir o canal de recuperação de senha.

**Critérios de aceite:**
- Dado um cadastro aceito, quando a conta é criada, então recebo no e-mail institucional um link com token aleatório imprevisível; o banco guarda só o hash do token.
- Dado que abro o link em até 24 h e ele não foi usado, quando a tela `/confirmar-email` envia o token por **POST** (nunca GET, para que o pré-carregamento de links pelos provedores de e-mail não consuma o token), então a conta passa a poder se autenticar e sou levado à tela de login.
- Dado um link expirado, já usado ou inválido, quando o abro, então vejo "link expirado ou inválido" e a opção de reenviar (US-02.2).

#### US-02.2 — Reenvio do link de confirmação

**Ref.:** RF02 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-02.1 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como pessoa com cadastro pendente, quero pedir um novo link, para não perder o cadastro se o primeiro e-mail sumir.

**Critérios de aceite:**
- Dado que informo minha matrícula/SIAPE na tela de reenvio (acessível pela tela de login e pela tela de link expirado), quando peço o reenvio, então a resposta é **sempre a mesma** ("se houver cadastro pendente, enviaremos um novo link"), exista ou não a conta.
- Dado um cadastro pendente dentro do prazo, quando o reenvio é feito, então um novo link é enviado, o anterior é invalidado e o prazo de 24 h recomeça.
- Dado que já pedi 3 reenvios na última hora para a mesma matrícula/SIAPE, quando peço o 4º, então nenhum e-mail é enviado (a resposta continua a mesma).

#### US-02.3 — Exclusão automática de cadastro pendente expirado

**Ref.:** RF02 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-02.1, TT-06 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como pessoa cuja matrícula foi usada num cadastro nunca confirmado, quero que esse cadastro expire, para eu poder me cadastrar.

**Critérios de aceite:**
- Dado um cadastro pendente cujo último link venceu há mais de 24 h, quando o job periódico roda (`ExclusaoCadastroPendenteJob`, agendado no mesmo mecanismo do leitor, SP-02), então a conta é excluída e a matrícula/SIAPE, o e-mail e o apelido ficam livres.
- Dado um cadastro pendente com reenvio feito há menos de 24 h, quando o job roda, então ele **não** é excluído.

#### US-03.1 — Login com sessão em cookie

**Ref.:** RF03, ADR 0007 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 1
**Depende de:** US-02.1, TT-06 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Usuário com conta confirmada, quero entrar com matrícula/SIAPE e senha e continuar logado ao reabrir o site, para avaliar refeições e fazer check-in.

**Critérios de aceite:**
- Dado um único campo de identificador, quando digito 9 dígitos, então é tratado como matrícula; com 7, como SIAPE; com outra quantidade, é rejeitado por formato **sem consultar o banco**.
- Dado credenciais corretas de conta confirmada, quando entro, então é criada uma sessão em cookie `HttpOnly`, `Secure` e `SameSite=Lax`, e sou levado à página inicial.
- Dado que recarrego a página ou reabro o site, quando a sessão ainda é válida, então continuo logado.
- Dado credenciais incorretas, quando entro, então vejo uma mensagem genérica, sem indicar se a matrícula/SIAPE existe.
- Dado credenciais corretas de conta **pendente**, quando entro, então vejo a orientação para confirmar o e-mail e a opção de reenvio (US-02.2).
- Dado credenciais corretas de conta **suspensa** ou **removida** (moderação, ADR 0004), quando entro, então o login é recusado com a mesma mensagem genérica.

#### US-03.2 — Bloqueio após tentativas malsucedidas

**Ref.:** RF03, Anexo A | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-03.1 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado 5 tentativas malsucedidas consecutivas para o mesmo identificador em 10 minutos, quando faço a 6ª, então novas tentativas ficam bloqueadas por 10 minutos, **mesmo com a senha correta**.
- Dado um login bem-sucedido, quando ele ocorre, então o contador de falhas é zerado.

#### US-03.3 — Sair da conta

**Ref.:** RF03, ADR 0007 (decisão de projeto) | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-03.1 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Usuário, quero sair da minha conta, principalmente num aparelho compartilhado.

**Critérios de aceite:**
- Dado que estou logado, quando toco em "Sair", então a sessão é encerrada no servidor, o cookie é apagado e volto a navegar como Visitante.

#### US-04.1 — Solicitar redefinição de senha

**Ref.:** RF04, L07 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 2
**Depende de:** US-03.1, SP-03 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado que informo uma matrícula/SIAPE, quando peço a redefinição, então a resposta é sempre "se houver conta, enviaremos o e-mail", exista ou não a conta.
- Dado que existe conta confirmada, quando peço, então recebo um link de uso único, válido por 1 hora.
- Dado 3 solicitações na última hora para a mesma matrícula/SIAPE, quando peço a 4ª, então nenhum e-mail é enviado.

#### US-04.2 — Redefinir senha pelo link

**Ref.:** RF04, ADR 0007 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 2
**Depende de:** US-04.1 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado um link válido, quando defino uma nova senha com pelo menos 8 caracteres, então a senha anterior deixa de valer e **todas as sessões ativas da conta são encerradas**.
- Dado um link expirado ou já usado, quando tento redefinir, então vejo "link expirado ou inválido" e a opção de pedir outro.

#### US-05.1 — Navegação sem login e convite ao cadastro

**Ref.:** RF05, RI01, RI06 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-03.1 | **Labels:** `epico:login`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado que não estou logado, quando acesso a URL raiz, então vejo o cardápio e a previsão de pico sem nenhum bloqueio.
- Dado que não estou logado, quando toco em "Avaliar" ou "Fazer check-in", então vejo um convite inline para entrar ou se cadastrar, sem erro genérico e sem sair da tela.
- Dado que chamo diretamente a API de avaliação ou de check-in sem sessão, quando a requisição chega, então ela é recusada (401).

---

### 4.6 Épico 2 — Cardápio

#### US-06.1 — Download semanal do PDF por campus

**Ref.:** RF06, ADR 0003 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz; reavaliar após SP-01) | **Onda:** 1
**Depende de:** SP-01, TT-03, TT-06 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Visitante, quero que o cardápio do Bandejão acompanhe o PDF publicado pelo RU sem ninguém da equipe precisar intervir.

**Critérios de aceite:**
- Dado que o RU publica um novo PDF para um campus, quando o cron roda na frequência definida em SP-02, então o novo cardápio aparece no sistema em até 24 h.
- Dado que o PDF já lido não mudou, quando o cron roda de novo, então nada é regravado.
- Dado um erro de rede ou HTTP no download, quando ocorre, então o tratamento é o de US-06.4.

#### US-06.2 — Extração de categorias, pratos e dietas

**Ref.:** RF06, RF07, RF09 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz; reavaliar após SP-01) | **Onda:** 1
**Depende de:** US-06.1 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado o PDF de um campus, quando lido, então cada página vira uma Refeição (café da manhã, almoço ou jantar) de cada dia presente no PDF, **somente** os dias e refeições que constam nele (ex.: almoço de sábado quando existir).
- Dado o texto "Arroz branco OU arroz integral", quando separado, então vira dois pratos; dado "Feijão carioca/preto", então continua um prato só ("/" não separa).
- Dado as linhas de prato principal (almoço/jantar) ou complemento (café da manhã), quando lidas, então cada prato recebe a dieta `padrao`, `ovolacto` ou `vegetariano_estrito`; as demais categorias ficam sem dieta.
- A regra de separação de pratos tem testes unitários que não dependem de PDF (`CardapioEstruturador.separarPratos`).

#### US-06.3 — Marcadores por posição e validação da legenda

**Ref.:** RF06, RF08, L03 | **Prioridade:** Alta | **Esforço:** a estimar (maior risco técnico do projeto) | **Onda:** 1
**Depende de:** US-06.2 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado os ícones de uma refeição, quando lidos, então cada prato fica associado aos marcadores cujos ícones aparecem junto a ele, pela posição.
- Dado que a legenda do PDF tem exatamente os 10 marcadores conhecidos, quando validada, então a leitura segue normalmente.
- Dado um ícone desconhecido, ou ícones que não podem ser associados a pratos, quando a refeição é lida, então o cardápio em texto é publicado mesmo assim, a refeição fica com status "informação de alérgenos indisponível" e é gerado um alerta (US-06.5).
- Nenhum Marcador novo é criado a partir do PDF: a tabela tem só os 10 da fixture.

#### US-06.4 — Manter o último cardápio válido quando a leitura falha

**Ref.:** RF06, RNF02 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-06.1 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado que o download ou a leitura do texto falha (ex.: mudança de formato), quando isso ocorre, então o último cardápio lido com sucesso continua sendo exibido, sem página vazia ou quebrada, e é gerado um alerta (US-06.5).
- Dado a falha, quando ocorre, então o restante do site continua funcionando (login, avaliação, check-in).

#### US-06.5 — Alerta de falha do leitor para a equipe

**Ref.:** RF06, ADR 0006 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 1
**Depende de:** US-06.3, US-06.4, SP-03 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como integrante da equipe, quero ser avisado por e-mail quando a leitura do cardápio falha, sem receber dezenas de e-mails pela mesma falha.

**Critérios de aceite:**
- Dado qualquer falha (legenda inválida, associação falhou, falha de leitura), quando ocorre, então um registro é gravado em `AlertaLeituraCardapio`, que serve de histórico, sempre.
- Dado a mesma combinação de campus e tipo de falha, quando ela se repete, então são enviados **no máximo 3 e-mails por dia**, com **intervalo mínimo de 6 h** entre eles (`ContadorAlerta`).
- Dado que a leitura daquele campus volta a funcionar, ou que começa um novo dia, quando isso ocorre, então o contador zera.
- Dado que o serviço de e-mail está fora do ar, quando o envio falha, então a leitura e o fallback de US-06.4 continuam sem interrupção.

#### US-07.1 — Cardápio real por campus, dia e refeição

**Ref.:** RF07, RF05, RNF03 | **Prioridade:** Alta | **Esforço:** Baixo (exibição) / Alto (apresentação refinada) (Matriz) | **Onda:** 1
**Depende de:** US-06.2, TT-05 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Visitante, quero abrir o site e ver direto o cardápio da refeição atual do meu campus, para decidir rápido o que comer.

**Critérios de aceite:**
- Dado a primeira visita, quando abro o site, então chego ao cardápio de um campus em **no máximo 3 toques**.
- Dado que escolhi um campus, quando volto ao site, então o campus está lembrado no aparelho e o cardápio abre sem nenhum toque; a rota `/cardapio/:campusId` também abre o campus direto (link compartilhável).
- Dado o horário atual, quando o cardápio abre, então é exibida a refeição **em andamento** ou, se nenhuma estiver, a **próxima do dia**, conforme os horários do Anexo A. A refeição não fica lembrada.
- Dado o campus e o dia, quando abro o seletor de refeição, então só aparecem as refeições que o PDF traz para aquele dia.
- Dado a semana vigente, quando troco de dia pelas abas, então a página não é recarregada.
- Dado um campus sem PDF da semana, quando o abro, então vejo "cardápio ainda não publicado".
- O aviso "cardápio sujeito a alteração" aparece sempre. As categorias aparecem em lista hierarquizada (a tabela do PDF não é reproduzida) e as linhas de dieta ficam em destaque.
- Os dados vêm de `GET /api/cardapio/` (ADR 0005), não mais do JSON do protótipo.

#### US-08.1 — Filtro de marcadores aplicado no backend

**Ref.:** RF08, ADR 0005, L04 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 1
**Depende de:** US-06.3, US-07.1 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como pessoa com restrição alimentar, quero marcar os marcadores que evito e ver quais pratos os contêm, sem ler o cardápio inteiro.

**Critérios de aceite:**
- Dado que seleciono "leite e derivados", quando o cardápio é pedido, então o PWA envia os marcadores como parâmetros e o backend devolve os pratos que os contêm **ainda visíveis**, com o alerta "Contém: leite e derivados".
- Dado que todos os pratos de uma categoria têm algum marcador selecionado, quando exibida, então a categoria mostra "sem opção compatível".
- Dado uma refeição com "informação de alérgenos indisponível", quando exibida, então o filtro aparece desativado, com o motivo.
- Dado que selecionei marcadores, quando troco de dia, refeição ou campus, ou reabro o site, então a seleção continua (lembrada no aparelho, sem login).
- O aviso fixo junto ao filtro diz que ele se baseia no cardápio oficial, sujeito a alteração; que a ausência de marcador não garante ausência do ingrediente; e que peixe e frutos do mar não são marcados.
- O código de filtro no cliente, herdado do protótipo (PROT-02), foi removido.

#### US-09.1 — Filtro de dieta aplicado no backend

**Ref.:** RF09, ADR 0005 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 1
**Depende de:** US-06.2, US-07.1 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado "Ovolactovegetariano", quando aplicado, então aparecem as linhas ovolactovegetariana e vegetariana estrita (prato principal ou complemento) e a linha padrão some.
- Dado "Vegetariano estrito", quando aplicado, então só a linha vegetariana estrita aparece entre as linhas de dieta.
- Dado qualquer dieta, quando aplicada, então as categorias comuns (saladas, guarnição, sopa etc.) continuam visíveis.
- Dado um filtro de dieta ativo, quando toco em "mostrar todas", então todas as linhas aparecem temporariamente, sem apagar a escolha salva.
- Dado dieta e marcadores escolhidos juntos, quando aplicados, então a dieta é aplicada primeiro e os marcadores depois, sobre o que sobrou.
- O código de filtro no cliente, herdado do protótipo (PROT-03), foi removido.

#### US-10.1 — Ícones dos marcadores nos pratos

**Ref.:** RF10 | **Prioridade:** Baixa | **Esforço:** Baixo (Matriz) | **Onda:** 3
**Depende de:** US-06.3, US-07.1 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:baixa`, `tipo:historia`

**Critérios de aceite:**
- Dado um prato com marcadores, quando exibido, então os ícones aparecem ao lado do nome, sem hover nem clique, **independentemente de filtro ativo**.
- Dado um prato sem marcadores, quando exibido, então nenhum ícone aparece.
- Dado uma refeição com "informação de alérgenos indisponível", quando exibida, então nenhum ícone aparece e o aviso explica o motivo.
- Cada ícone tem texto alternativo com o nome do marcador (leitores de tela).

#### US-18.1 — Cardápio da semana seguinte

**Ref.:** RF18 | **Prioridade:** Média | **Esforço:** a estimar | **Onda:** 3
**Depende de:** US-07.1 | **Labels:** `epico:cardapio`, `release:r2`, `prioridade:media`, `tipo:historia`

**Critérios de aceite:**
- Dado que o PDF da semana seguinte de um campus foi lido com sucesso, quando abro o cardápio, então aparece a aba da semana seguinte, na mesma navegação por abas, sem recarregar a página.
- Dado que ele ainda não foi lido, quando abro o cardápio, então só a semana vigente aparece.

---

### 4.7 Épico 3 — Fila e Previsão de Pico

#### US-11.1 — Check-in no RU

**Ref.:** RF11, RI01, RI03 | **Prioridade:** Média | **Esforço:** Alto (Matriz) | **Onda:** 2 (marco MC-01)
**Depende de:** US-03.1, US-12.1, TT-03 | **Labels:** `epico:fila`, `release:r2`, `prioridade:media`, `tipo:historia`

**História:** Como Usuário no RU, quero registrar minha presença, para alimentar a previsão de pico de todo mundo.

**Critérios de aceite:**
- Dado que estou logado e dentro do horário da refeição (Anexo A), quando faço check-in confirmado por GPS (US-12.1), então ele é registrado com campus, tipo de refeição e data.
- Dado que já fiz check-in nessa refeição hoje, quando tento de novo, então sou informado que já fiz check-in.
- Dado dois toques rápidos no botão, quando as duas requisições chegam juntas, então só um check-in é gravado (**UNIQUE `(usuario, campus, tipo_refeicao, data)` no banco**).
- Dado que estou fora do horário da refeição, quando tento, então sou informado do horário da refeição.
- Dado que existe cardápio publicado para a semana e ele **não** lista essa refeição naquele dia, quando tento, então sou informado de que a refeição não é servida.
- Dado que o cardápio da semana ainda não foi publicado ou a leitura falhou, quando tento dentro do horário, então o check-in é aceito normalmente.
- Dado um check-in feito, quando procuro uma forma de desfazê-lo, então ela não existe.

#### US-12.1 — Confirmação do check-in por GPS

**Ref.:** RF12, RI08, RI09 | **Prioridade:** Média | **Esforço:** Alto (Matriz) | **Onda:** 2 (marco MC-01)
**Depende de:** SP-04, TT-05 | **Labels:** `epico:fila`, `release:r2`, `prioridade:media`, `tipo:historia`

**Critérios de aceite:**
- Dado que nunca fiz check-in, quando toco em "Fazer check-in", então sou informado de que o navegador vai pedir permissão de localização.
- Dado que nego a permissão, quando tento, então vejo "check-in não é possível sem permissão de localização", e nenhuma requisição é enviada.
- Dado que estou dentro do raio do RU do campus escolhido, quando envio, então o check-in é confirmado.
- Dado que estou fora do raio, **inclusive no RU de outro campus ou no Restaurante Executivo**, quando envio, então vejo que o check-in não pôde ser confirmado por localização, e posso tentar de novo depois.
- Dado uma tentativa que chegou à conferência de GPS, quando termina, então é gravada uma `TentativaCheckin` com usuário, campus, refeição, data/hora e resultado (confirmado/rejeitado). Tentativas recusadas antes (horário, duplicidade, refeição não servida) **não** são gravadas.
- Dado qualquer desfecho, quando a requisição termina, então as coordenadas não existem em nenhuma tabela, log de aplicação ou log de acesso do servidor, nem ficam no estado do frontend.

#### US-13.1 — Previsão de pico por faixa de horário

**Ref.:** RF13, RI05, L08 | **Prioridade:** Média | **Esforço:** a estimar (a Matriz só avaliou uma versão estática, que foi descartada) | **Onda:** 3
**Depende de:** US-11.1, MC-02 | **Labels:** `epico:fila`, `release:r2`, `prioridade:media`, `tipo:historia`

**História:** Como Visitante ou Usuário, quero ver em que horário a fila costuma estar mais cheia, para escolher quando ir ao RU.

**Critérios de aceite:**
- Dado campus, refeição e dia escolhidos, quando abro a previsão, sem precisar de login, então vejo faixas de 15 minutos cobrindo o horário da refeição, no fuso `America/Sao_Paulo`.
- Dado a janela das últimas 4 semanas no mesmo dia da semana, quando calculada, então **"dia com dados" é um dia com pelo menos 1 check-in confirmado naquela refeição e campus**. Nesses dias, uma faixa sem check-in conta como zero, e os dias sem nenhum check-in ficam fora da média.
- Dado a média de cada faixa, quando classificada pela razão com a faixa mais cheia, então: menos de 25% é **vazia**; de 25% a menos de 50%, **curta**; de 50% a menos de 75%, **moderada**; 75% ou mais, **longa**.
- Dado a faixa mais cheia, quando exibida, então ela é destacada como pico. Em caso de empate, todas as empatadas são destacadas.
- Dado menos de 3 dias com dados na janela, quando abro a previsão, então vejo "dados insuficientes", sem nenhum valor de reserva.
- A resposta traz só agregados, nunca dados de conta ou de check-ins individuais.
- Os cálculos (janela, faixas, suficiência, média, classificação) têm testes unitários separados.

#### US-14.1 — Nível da fila agora

**Ref.:** RF14, L08 | **Prioridade:** Baixa | **Esforço:** Alto (Matriz) | **Onda:** 3
**Depende de:** SP-05, US-11.1 | **Labels:** `epico:fila`, `release:r2`, `prioridade:baixa`, `tipo:historia`

**Critérios de aceite:**
- Dado uma refeição em andamento, quando abro a fila, então vejo o nível atual (vazia, curta, moderada ou longa), calculado com a janela e os limiares definidos em SP-05.
- Dado poucos check-ins recentes, abaixo do mínimo definido em SP-05, quando abro a fila, então vejo "dados insuficientes" em vez de "vazia".
- Dado que nenhuma refeição está em andamento, quando abro a fila, então o nível agora não aparece.
- *(Os critérios serão completados por SP-05.)*

---

### 4.8 Épico 4 — Avaliação das Refeições

#### US-15.1 — Avaliar a refeição

**Ref.:** RF15, RI01, RNF04 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 2
**Depende de:** US-03.1, US-07.1 | **Labels:** `epico:avaliacao`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como Usuário, quero dar de 1 a 5 estrelas à refeição e comentar, para ajudar quem ainda não decidiu se come no RU.

**Critérios de aceite:**
- Dado que estou logado, quando avalio uma refeição (campus + dia + tipo) com nota de 1 a 5 e comentário opcional de até 500 caracteres, então a avaliação é salva ligada à minha conta. Não existe nota por prato.
- Dado que não escolhi nota, ou o comentário tem mais de 500 caracteres, quando envio, então a avaliação é rejeitada com o motivo (validado no serializer **e** por CHECK no banco).
- Dado uma refeição de outro dia, ou do dia atual que ainda não começou, quando tento avaliar, então a avaliação fica indisponível e o motivo é mostrado.
- Dado que já avaliei essa refeição, quando avalio de novo até as 23h59 do mesmo dia, então a avaliação anterior é **editada**, não duplicada.
- Dado um comentário com HTML ou script, quando exibido, então aparece como texto puro.
- O campo demonstrativo do protótipo (PROT-05) passa a gravar de verdade.

#### US-15.2 — Ver as avaliações da refeição

**Ref.:** RF15, RI10, RNF07, L09 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 2
**Depende de:** US-15.1 | **Labels:** `epico:avaliacao`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado uma refeição da semana vigente, inclusive de dias passados, quando exibida, então vejo a nota média, a quantidade de avaliações e os comentários com o **apelido** do autor, mesmo sem login.
- Dado uma refeição sem avaliações, quando exibida, então vejo "sem avaliações ainda".
- Dado qualquer resposta da API de avaliações, quando inspecionada, então não contém matrícula/SIAPE nem e-mail.
- Dado uma avaliação de conta removida, quando exibida, então o autor aparece como "usuário removido".
- Dado uma refeição de semana anterior, quando procuro na tela do cardápio, então ela não aparece ali (só no histórico, US-16.1), mas continua armazenada.
- As avaliações de exemplo do protótipo (PROT-04) não vão para o banco de produção.

#### US-16.1 — Histórico de refeições anteriores

**Ref.:** RF16 | **Prioridade:** Média | **Esforço:** Baixo (Matriz) | **Onda:** 3
**Depende de:** US-15.2 | **Labels:** `epico:avaliacao`, `release:r2`, `prioridade:media`, `tipo:historia`

**Critérios de aceite:**
- Dado a tela de histórico (`/avaliacoes`), quando navego por campus, data e refeição de semanas anteriores, então vejo o cardápio completo, a nota média e os comentários com apelido, só para leitura.
- Dado uma refeição passada, quando procuro onde avaliá-la, então essa opção não existe.
- Dado uma refeição sem avaliações, quando exibida, então vejo "sem avaliações ainda".
- Dado uma data anterior à primeira leitura do sistema, quando a procuro, então ela não está disponível (não há carga de PDFs antigos).

---

### 4.9 Transversal

#### US-17.1 — Identidade visual em todas as telas

**Ref.:** RF17, RNF03 | **Prioridade:** Alta | **Esforço:** Baixo (Matriz) | **Onda:** 3 (revisão contínua)
**Depende de:** PROT-06 | **Labels:** `epico:transversal`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado o guia de estilo da equipe, versionado no repositório, quando comparo lado a lado todas as telas da R2 (inclusive as novas: cadastro, login, fila, histórico), então paleta, tipografia e espaçamento são os mesmos.
- Dado uma tela de 360 px, quando uso qualquer funcionalidade, então nada fica cortado nem exige rolagem horizontal.

#### US-RNF05.1 — PWA instalável

**Ref.:** RNF05 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 3
**Depende de:** TT-06 | **Labels:** `epico:transversal`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como frequentador do RU, quero instalar o Bandejão na tela inicial do celular, para abrir o cardápio como um aplicativo.

**Critérios de aceite:**
- Dado Chrome, Edge, Firefox ou Safari nas duas versões mais recentes, quando acesso o site, então ele é instalável (manifest válido, ícones, service worker registrado).
- Dado que estou sem conexão, quando abro o app instalado, então vejo o último cardápio carregado ou uma mensagem clara de "sem conexão", nunca uma tela em branco.
- Dado o app instalado, quando abro, então a sessão (ADR 0007) e o campus lembrado continuam valendo.

#### US-RNF07.1 — Aviso de privacidade

**Ref.:** RNF07, RI09, RI10 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 3
**Depende de:** — | **Labels:** `epico:transversal`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado a página pública de privacidade, linkada no rodapé e no cadastro, quando a leio, então ela diz quais dados são coletados (matrícula/SIAPE, e-mail, apelido), para quê (login, recuperação de senha, identificação do autor de avaliações), que a localização é usada só na conferência do check-in e não é guardada, e como pedir a exclusão da conta.
- O texto do aviso mostrado no cadastro (US-01.1) é o mesmo resumo dessa página.

#### US-RNF08.1 — API respeita os estados de moderação

**Ref.:** RNF08, ADR 0004 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 2
**Depende de:** US-03.1, US-15.2 | **Labels:** `epico:transversal`, `release:r2`, `prioridade:alta`, `tipo:historia`

**História:** Como equipe, quero que as alterações de moderação feitas direto no banco tenham efeito imediato no site.

**Critérios de aceite:**
- Dado `AVALIACAO.oculta = true`, quando a refeição é exibida, então a avaliação não aparece **e não entra na média nem na contagem**.
- Dado `USUARIO.status = suspenso`, quando a conta tenta login, então ele é recusado (US-03.1), e as sessões já abertas deixam de valer na próxima requisição.
- Dado uma conta suspensa, quando suas avaliações são exibidas, então continuam visíveis, a menos que tenham sido ocultadas uma a uma.
- Dado `USUARIO.status = removido`, quando suas avaliações são exibidas, então aparecem como "usuário removido".
- Os procedimentos correspondentes estão no roteiro de moderação (TT-07).

#### US-RNF08.2 — Canal de contato para reclamações

**Ref.:** RNF08, RNF07, L01 | **Prioridade:** Alta | **Esforço:** a estimar | **Onda:** 3
**Depende de:** — | **Labels:** `epico:transversal`, `release:r2`, `prioridade:alta`, `tipo:historia`

**Critérios de aceite:**
- Dado qualquer página, quando olho o rodapé, então vejo um canal de contato (e-mail do projeto) para reclamações, contestação de matrícula e pedidos de exclusão de conta.
- Dado a mensagem de duplicidade no cadastro (US-01.5), quando exibida, então ela aponta para esse canal.

---

## 5. Matriz de rastreabilidade (requisito → itens)

| Requisito | R1 | R2 |
|---|---|---|
| RF01 | — | US-01.1, US-01.2, US-01.3, US-01.4, US-01.5 |
| RF02 | — | US-02.1, US-02.2, US-02.3 |
| RF03 | — | US-03.1, US-03.2, US-03.3 |
| RF04 | — | US-04.1, US-04.2 |
| RF05 | PROT-01 | US-05.1 |
| RF06 | — | SP-01, US-06.1, US-06.2, US-06.3, US-06.4, US-06.5 |
| RF07 | PROT-01 | US-07.1 |
| RF08 | PROT-02 | US-08.1 |
| RF09 | PROT-03 | US-09.1 |
| RF10 | — | US-10.1 |
| RF11 | — | US-11.1, MC-01 |
| RF12 | — | SP-04, US-12.1 |
| RF13 | — | US-13.1, MC-02 |
| RF14 | — | SP-05, US-14.1 |
| RF15 | PROT-04, PROT-05 | US-15.1, US-15.2 |
| RF16 | — | US-16.1 |
| RF17 | PROT-06 | US-17.1 |
| RF18 | — | US-18.1 |
| RNF01 | — | TT-08 |
| RNF02 | — | US-06.4, TT-09 |
| RNF03 | PROT-01 | US-07.1, US-17.1 |
| RNF04 | — | DoD, US-02.1, US-15.1 |
| RNF05 | — | US-RNF05.1 |
| RNF06 | — | DoD, TT-01, TT-02 |
| RNF07 | — | US-01.1, US-RNF07.1 |
| RNF08 | — | US-RNF08.1, US-RNF08.2, TT-07 |
| RI01 | — | US-05.1, US-11.1, US-15.1 |
| RI02, RI08 | — | US-06.1 (só RUs oficiais), SP-04 (raio exclui o Executivo) |
| RI03 | — | US-11.1 |
| RI04 | — | DoD |
| RI05 | — | US-13.1 |
| RI06 | PROT-01 | US-05.1 |
| RI07 | — | US-01.3, US-01.4 |
| RI09 | — | DoD, US-12.1 |
| RI10 | — | DoD, US-15.2 |

---

## 6. Decisões que moldaram este backlog

Todas registradas em 28/09/2026 e refletidas nas histórias acima. As que exigem mudança nos documentos estão em `correcoes-documentos.md`.

| # | Decisão |
|---|---|
| 1 | Releases: R1 = protótipo frontend (28/09); R2 = produto completo com todos os RFs (25/11). |
| 2 | Filtragem no cliente só no protótipo. A ADR 0005 (filtro no backend) vale para a R2. |
| 3 | As Views lendo JSON direto é limitação conhecida da R1, e não defeito. A R2 introduz Pinia, stores e `apiClient` (TT-05). |
| 4 | Check-in: `Checkin` e `TentativaCheckin` são tabelas separadas, sem FK para Refeição, com UNIQUE `(usuario, campus, tipo_refeicao, data)`. |
| 5 | Check-in é recusado se o cardápio publicado não lista a refeição, e aceito se a leitura falhou ou o cardápio não foi publicado. |
| 6 | Só as tentativas que chegam à conferência de GPS geram `TentativaCheckin`. |
| 7 | RF13: "dia com dados" é um dia com pelo menos 1 check-in; faixas vazias desse dia contam como zero; empate destaca todas as faixas. |
| 8 | Matrícula/SIAPE fica em texto claro com UNIQUE e acesso restrito (ADR 0008). |
| 9 | Novos estados de moderação: `AVALIACAO.oculta` e `USUARIO.status = suspenso`, respeitados pela API. |
| 10 | `AlertaLeituraCardapio` (histórico) e `ContadorAlerta` (limite de e-mails) convivem. |
| 11 | Duplicidade no cadastro recebe mensagem combinada, com link para o canal de contato. |
| 12 | Cardápio via `GET /api/cardapio/` com parâmetros de query (ADR 0005); confirmação de e-mail por POST; contrato em OpenAPI. |
| 13 | Sessão em cookie `HttpOnly` (ADR 0007). |
| 14 | Reenvio de confirmação pela matrícula/SIAPE, com resposta sempre igual e limite de 3 por hora. |
| 15 | Ficam lembrados no aparelho o campus e os filtros. A refeição exibida segue sempre o RF07. |
| 16 | RF10 e RF14 entram na R2; o RF14 depende de SP-05. |
| 17 | Marco: check-in em produção até 03/11, e coleta de check-ins pela equipe nas quartas 04, 11 e 18/11. |

---

## 7. Pendências fora do backlog

- **Q21:** o time de frontend vai confirmar se o protótipo terá alguma tela de login. Isso não afeta a R2: as telas reais de autenticação estão em US-01.x a US-04.x.

---

## 8. Correspondência com o backlog anterior

Para quem já abriu issues no GitHub com os IDs antigos:

| Antigo | Situação | Novo |
|---|---|---|
| US-01 Cadastro | Reescrito: duas etapas, matrícula/apelido extraídos do e-mail | US-01.1 a US-01.5 |
| US-02 Login (por e-mail) | Reescrito: login por matrícula/SIAPE, sessão em cookie | US-03.1 a US-03.3 |
| US-03 Navegação sem autenticação | Mantido | PROT-01, US-05.1 |
| US-04 Login validado por matrícula/SIAPE | **Removido**: não há validação real; só formato (US-01.3, US-01.4) | — |
| US-05 Leitura automatizada do PDF | Dividido | US-06.1 a US-06.5 |
| US-06 Exibição por dia e campus | Mantido e ampliado (refeição padrão, "não publicado") | PROT-01, US-07.1 |
| US-07 Filtro de restrições/alergias | Reescrito como filtro de **marcadores** (sem "frutos do mar", que o cardápio não marca) | PROT-02, US-08.1 |
| — | Novo | PROT-03, US-09.1 (filtro de dieta) |
| US-08 Design refinado | Absorvido | PROT-01, US-07.1, US-17.1 |
| US-09 Ícones de alérgenos | Renomeado para marcadores | US-10.1 |
| US-10 Previsão estática | **Removido**: não há versão estática | US-13.1 |
| US-11 Nível da fila por votação | **Removido** (RI05: sem votação) | US-14.1 (nível agora por check-in) |
| US-12 Painel informativo da fila | **Removido**, absorvido | US-13.1, US-14.1 |
| US-13 Check-in no RU | Mantido | US-11.1 |
| US-14 GPS para confirmar voto | Reescrito: GPS confirma o check-in | US-12.1 |
| US-15 Confirmação de check-in por GPS | Fundido | US-12.1 |
| US-16 Avaliação por estrelas | Reescrito: avaliação por **refeição**, não por prato | PROT-04, PROT-05, US-15.1, US-15.2 |
| US-17 Avaliações de pratos anteriores | Reescrito como histórico de refeições | US-16.1 |
| US-18 Design do site | Mantido | PROT-06, US-17.1 |
