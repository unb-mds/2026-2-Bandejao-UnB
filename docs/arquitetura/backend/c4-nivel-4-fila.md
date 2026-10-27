# Arquitetura C4 — Nível 4 (Fila e Previsão de Pico) — Bandejão

> Detalha, em diagrama de classes, o componente **Fila**, desenhado no
> Nível 3 do backend (ver `c4-nivel-3-backend.md`). Cobre o Épico Fila e
> Previsão de Pico: check-in no RU (RF11), confirmação por GPS (RF12),
> previsão de pico por faixa de horário (RF13), pergunta de saída da fila
> (RF21) e, como item de Backlog, nível de fila "agora" (RF14). O cálculo do
> tempo de espera e da espera estimada (RF22) ainda não está desenhado.
>
> Há dois diagramas: **4a**, check-in e previsão de pico, e **4b**, pergunta
> de saída da fila.
>
> Todo o épico é **Release 2 / Backlog**: nada aqui faz parte do MVP. O
> diagrama existe para que a decomposição já esteja pensada quando a
> Release 2 começar.
>
> Como nos outros Níveis 4, este componente só **lê** models de outros
> componentes (`Conta`, do Cadastro/Autenticação) por chave estrangeira. A
> única chamada a outro componente é a da pontuação: depois de salvar um
> check-in confirmado ou a resposta à pergunta de saída, a Fila chama o
> `PontuacaoService` da Gamificação na mesma transação (ver nota do Nível 3
> e `c4-nivel-4-gamificacao.md`).
>
> **Endpoints deste componente:**
>
> | Endpoint | Acesso | View |
> |---|---|---|
> | `POST /api/checkins/` | Logado | `CheckinView` |
> | `GET /api/fila/previsao/?campus=&refeicao=&data=` | Público | `PrevisaoView` |
> | `GET /api/fila/pergunta-pendente/` | Logado | `PerguntaSaidaPendenteView` |
> | `POST /api/fila/respostas-saida/` | Logado | `RespostaSaidaView` |
> | `POST /api/fila/perguntas-saida/{id}/dispensa/` | Logado | `DispensaPerguntaSaidaView` |

## Nível 4a — Check-in e previsão de pico

```mermaid
classDiagram
  class CheckinView {
    +post(request) Response
  }
  class PrevisaoView {
    +get(campus: Campus, tipoRefeicao: str, data: date) Response
  }
  class NivelAgoraView {
    <<backlog>>
    +get(campus: Campus, tipoRefeicao: str) Response
  }

  class CheckinService {
    +registrar(conta: Conta, campus: Campus, tipoRefeicao: str, coordenadas: Coordenadas, agora: datetime) CheckinRegistrado
  }
  class CheckinRegistrado {
    +checkin: Checkin
    +pontos: ResultadoPontuacao
    +perguntaDevidaEm: datetime
  }
  class AvisoPrivacidadePendenteError
  class JanelaCheckinValidator {
    +dentroDoHorario(tipoRefeicao: str, agora: datetime) bool
  }
  class ConfirmacaoLocalizacaoService {
    +confirmar(campus: Campus, coordenadas: Coordenadas) bool
  }
  class DistanciaGeografica {
    +metros(a: Coordenadas, b: Coordenadas) float
  }
  class Coordenadas {
    <<transitório, nunca persistido>>
    +latitude: float
    +longitude: float
  }
  class CheckinForaDoHorarioError
  class CheckinDuplicadoError
  class LocalizacaoNaoConfirmadaError

  class CheckinRepository {
    +existeCheckin(conta: Conta, campus: Campus, tipoRefeicao: str, data: date) bool
    +salvarCheckin(checkin: Checkin) Checkin
    +registrarTentativa(tentativa: TentativaCheckin) void
    +contarPorFaixa(campus: Campus, tipoRefeicao: str, datas: list~date~, faixas: list~FaixaHorario~) list~ContagemDia~
  }
  class Checkin {
    +id: UUID
    +contaId: UUID
    +campus: Campus
    +tipoRefeicao: str
    +data: date
    +registradoEm: datetime
    +pontosConcedidosEm: datetime
  }
  class TentativaCheckin {
    +id: UUID
    +contaId: UUID
    +campus: Campus
    +tipoRefeicao: str
    +dataHora: datetime
    +resultado: ResultadoTentativa
  }
  class ResultadoTentativa {
    <<enumeration>>
    CONFIRMADO
    REJEITADO
  }
  class ContagemDia {
    +data: date
    +checkinsPorFaixa: list~int~
  }

  class PrevisaoService {
    +calcular(campus: Campus, tipoRefeicao: str, data: date) PrevisaoPico
  }
  class JanelaHistoricoResolver {
    +datasDaJanela(data: date) list~date~
  }
  class FaixaHorarioGenerator {
    +faixas(tipoRefeicao: str) list~FaixaHorario~
  }
  class FaixaHorario {
    +inicio: time
    +fim: time
  }
  class SuficienciaDadosValidator {
    +suficiente(contagens: list~ContagemDia~) bool
  }
  class MediaPorFaixaCalculator {
    +calcular(contagens: list~ContagemDia~) list~float~
  }
  class ClassificadorNivelFila {
    +classificar(mediaFaixa: float, mediaMaxima: float) NivelFila
  }
  class NivelFila {
    <<enumeration>>
    VAZIA
    CURTA
    MODERADA
    LONGA
  }
  class PrevisaoPico {
    +campus: Campus
    +tipoRefeicao: str
    +data: date
    +status: StatusPrevisao
    +faixas: list~FaixaPrevista~
  }
  class StatusPrevisao {
    <<enumeration>>
    DISPONIVEL
    DADOS_INSUFICIENTES
  }
  class FaixaPrevista {
    +inicio: time
    +fim: time
    +nivel: NivelFila
    +ehPico: bool
  }

  class NivelAgoraService {
    <<backlog>>
    +calcular(campus: Campus, tipoRefeicao: str, agora: datetime) NivelFila
  }

  class HorariosRefeicaoConfig {
    <<Anexo A, compartilhada>>
    +horarioCafe: tuple
    +horarioAlmoco: tuple
    +horarioJantar: tuple
  }
  class LocalizacaoRUConfig {
    <<Anexo A>>
    +centro(campus: Campus) Coordenadas
    +raioMetros(campus: Campus) int
  }
  class ParametrosFilaConfig {
    <<Anexo A>>
    +faixaMinutos: int = 15
    +janelaSemanas: int = 4
    +minDiasDistintos: int = 3
    +cortes: tuple = 25, 50, 75
  }

  class Conta {
    <<Cadastro/Autenticação>>
    +id: UUID
    +avisoPrivacidadePendente() bool
  }

  class PerguntaSaidaService {
    <<ver diagrama 4b>>
    +criar(checkin: Checkin, agora: datetime) PerguntaSaida
  }

  class PontuacaoService {
    <<App Gamificação>>
    +registrarContribuicao(conta: Conta, tipo: TipoContribuicao, origemId: UUID, refeicao: RefeicaoRef) ResultadoPontuacao
  }
  class ResultadoPontuacao {
    <<App Gamificação>>
    +total: int
  }

  CheckinView --> CheckinService : registrar()
  PrevisaoView --> PrevisaoService : calcular()
  NivelAgoraView --> NivelAgoraService : calcular()

  CheckinService ..> Conta : 0. aviso de privacidade aceito?
  CheckinService ..> AvisoPrivacidadePendenteError : lança se pendente (RF11)
  CheckinService --> JanelaCheckinValidator : 1. valida horário
  JanelaCheckinValidator ..> CheckinForaDoHorarioError : lança se fora da refeição
  JanelaCheckinValidator --> HorariosRefeicaoConfig : lê
  CheckinService --> CheckinRepository : 2. verifica duplicidade
  CheckinRepository ..> CheckinDuplicadoError : lança se já existe (RI03)
  CheckinService --> ConfirmacaoLocalizacaoService : 3. confirma localização
  ConfirmacaoLocalizacaoService --> DistanciaGeografica : calcula distância ao RU
  ConfirmacaoLocalizacaoService --> LocalizacaoRUConfig : lê centro e raio
  ConfirmacaoLocalizacaoService ..> LocalizacaoNaoConfirmadaError : lança se fora do raio
  ConfirmacaoLocalizacaoService ..> Coordenadas : usa e descarta
  CheckinService --> CheckinRepository : 4. registra tentativa / salva check-in
  CheckinService --> Checkin : cria, se confirmado
  CheckinService --> PontuacaoService : 5. registra contribuição (mesma transação)
  CheckinService --> PerguntaSaidaService : 6. cria pergunta pendente (mesma transação)
  CheckinService --> CheckinRegistrado : devolve
  CheckinRegistrado --> ResultadoPontuacao : tem

  CheckinRepository ..> Checkin : grava/lê
  CheckinRepository ..> TentativaCheckin : grava
  CheckinRepository --> ContagemDia : produz
  TentativaCheckin --> ResultadoTentativa : tem

  PrevisaoService --> JanelaHistoricoResolver : 1. datas da janela
  PrevisaoService --> FaixaHorarioGenerator : 2. faixas da refeição
  PrevisaoService --> CheckinRepository : 3. conta check-ins por faixa
  PrevisaoService --> SuficienciaDadosValidator : 4. dados suficientes?
  PrevisaoService --> MediaPorFaixaCalculator : 5. média por faixa
  PrevisaoService --> ClassificadorNivelFila : 6. nível de cada faixa
  PrevisaoService --> PrevisaoPico : monta
  JanelaHistoricoResolver --> ParametrosFilaConfig : lê
  FaixaHorarioGenerator --> ParametrosFilaConfig : lê
  FaixaHorarioGenerator --> HorariosRefeicaoConfig : lê
  SuficienciaDadosValidator --> ParametrosFilaConfig : lê
  ClassificadorNivelFila --> ParametrosFilaConfig : lê
  FaixaHorarioGenerator --> FaixaHorario : produz
  ClassificadorNivelFila --> NivelFila : produz
  PrevisaoPico --> StatusPrevisao : tem
  PrevisaoPico *-- FaixaPrevista
  FaixaPrevista --> NivelFila : tem

  NivelAgoraService --> CheckinRepository : lê check-ins recentes
  NivelAgoraService --> NivelFila : produz

  Checkin --> Conta : pertence a (FK)
  TentativaCheckin --> Conta : pertence a (FK)
```

### Notas do diagrama (4a)

- **Passo 0, aviso de privacidade (RF11, RNF07.1).** Quem já tinha conta
  antes da Release 2 só faz o primeiro check-in depois de dar ciência ao
  aviso de privacidade atualizado. O `CheckinService` consulta
  `Conta.avisoPrivacidadePendente()` (método do model do
  Cadastro/Autenticação, lido como os demais models de outros componentes,
  sem seta no Nível 3) e, se for verdadeiro, lança
  `AvisoPrivacidadePendenteError`, que a `CheckinView` devolve como
  `403` com `"codigo": "aviso_privacidade_pendente"`. É o primeiro passo
  porque é o mais barato e porque não faz sentido pedir GPS a quem ainda não
  aceitou o aviso. O PWA normalmente mostra o aviso antes, pelo indicador da
  sessão (ver `c4-nivel-4-cadastro-autenticacao.md`); este passo é a
  garantia no servidor.
- **Passo 6, pergunta de saída (RF21.1).** Na mesma transação do check-in
  confirmado, o `PerguntaSaidaService` cria a pergunta pendente, com
  `devidaEm` = hora do check-in + 15 min e `expiraEm` = hora do check-in +
  60 min (Anexo A). O `CheckinRegistrado` devolve `perguntaDevidaEm`, para o
  PWA agendar um aviso local e saber quando consultar a pergunta pendente
  (ver diagrama 4b).
- **Resposta do `POST /api/checkins/` (201):**

  ```json
  {
    "checkin": {"id": "…", "campus": 1, "tipoRefeicao": "almoco", "data": "2026-10-27"},
    "pontos": {"total": 10, "contribuicao": 10, "avaliacaoLiberada": 0, "bonusSemana": 0},
    "perguntaDevidaEm": "2026-10-27T12:15:00-03:00"
  }
  ```

  Rejeições: `403` (`aviso_privacidade_pendente`) e `422` com o motivo
  (`fora_do_horario`, `checkin_duplicado` ou `localizacao_nao_confirmada`).

- **`Coordenadas` nunca é persistida nem registrada em log** (RI09, RF12). O
  objeto nasce da requisição, é usado só por `ConfirmacaoLocalizacaoService`
  para comparar a distância com o raio do RU e descartado; nenhum model
  (`Checkin`, `TentativaCheckin`) tem campo de latitude/longitude. Na
  implementação, isso vale também para o log de acesso do servidor: o corpo
  da requisição de check-in não deve ser gravado.
- **A ordem das validações do `CheckinService` é deliberada**: aviso de
  privacidade (passo 0), horário, depois duplicidade, depois localização —
  do mais barato ao mais caro, e de
  modo que uma tentativa que já seria rejeitada por outro motivo não
  dependa do GPS. Como a conferência de localização é o passo que o RF12
  descreve como "cada tentativa registra usuário, campus, refeição, data/hora
  e resultado", desenhei `TentativaCheckin` como gravada a partir dessa
  etapa (confirmada ou rejeitada). **Ponto para alinhar:** o texto do RF12
  não deixa claro se tentativas rejeitadas por horário ou por duplicidade
  também devem gerar `TentativaCheckin`; na leitura literal, não.
- **O passo 5 pontua o check-in confirmado, e só ele.** Depois de salvar o
  `Checkin`, o `CheckinService` chama
  `PontuacaoService.registrarContribuicao(conta, CHECKIN, checkin.id,
  refeicao)`, da Gamificação. Tentativa rejeitada não chega a esse passo e
  não pontua (RN09). O salvamento do `Checkin` e a pontuação ficam na
  **mesma `transaction.atomic()`**: se a pontuação falhar, o check-in não é
  gravado e o usuário recebe erro e pode tentar de novo, em vez de ficar com
  um check-in sem pontos que ninguém consegue recalcular depois (ADR 0011).
  A `TentativaCheckin` rejeitada continua sendo gravada fora dessa
  transação.
- **A `refeicao` enviada à Gamificação é a do próprio check-in**: campus,
  tipo de refeição e data do `Checkin` já confirmado pelo GPS, no horário de
  Brasília. Nunca é um campo vindo do PWA nem o campus detectado no aparelho
  (RN09, ADR 0009, L13). O `PontuacaoService` não olha horário, faixa nem
  nível da fila para decidir os pontos (RI11).
- **`CheckinRegistrado` leva os pontos de volta à `CheckinView`**, que os
  devolve na resposta do 201 para o aviso "+10 pontos" (RF24.2). O
  `ResultadoPontuacao.total` pode passar de 10 quando o mesmo check-in
  também libera os pontos de uma avaliação já feita na refeição ou o bônus
  da semana; o detalhamento está em `c4-nivel-4-gamificacao.md`.
- **`Checkin.pontosConcedidosEm` é o marcador de "pontos já concedidos"**
  (ADR 0011). Quem o preenche é o `PontuacaoService`, no mesmo passo 5; é o
  único campo da Fila que a Gamificação escreve. Segue a recomendação da
  decisão 4 da lista de ajustes (marcador nos registros de origem), que
  ainda precisa ser confirmada pelas duplas.
- **`CheckinDuplicadoError` também é a resposta a uma corrida.** Além da
  verificação prévia em `existeCheckin`, o banco deve ter restrição de
  unicidade em (conta, campus, tipo de refeição, data): um duplo toque no
  botão pode disparar duas requisições simultâneas, e só a restrição do
  banco garante o RI03 nesse caso. A `IntegrityError` resultante é
  convertida no mesmo erro de duplicidade. Tentativa rejeitada não conta
  como check-in (RF11), então o usuário pode tentar de novo depois de sair
  do raio e voltar.
- **`Checkin` guarda campus + tipo de refeição + data, e não uma FK para
  `Refeicao` (Cardápio).** Assim, o check-in e a previsão continuam
  funcionando mesmo que a leitura do PDF do cardápio falhe naquela semana.
  **Ponto para alinhar:** o Anexo A diz que "os dias e as refeições
  servidos vêm do PDF"; se a equipe quiser recusar check-in em refeição que
  o PDF não lista para aquele dia, o `JanelaCheckinValidator` passa a
  consultar `Refeicao` e a fila fica dependente da leitura do cardápio.
- **A previsão (RF13) é calculada sob demanda, em seis passos separados**,
  cada um com regra própria e testável sem PDF nem interface: janela de 4
  semanas no mesmo dia da semana, faixas de 15 minutos, suficiência de dados
  (3 dias distintos), média por faixa, e classificação pelos cortes de
  25/50/75%. Todos os números vêm de `ParametrosFilaConfig` e
  `HorariosRefeicaoConfig` (Anexo A), não de constantes espalhadas.
  `HorariosRefeicaoConfig` é a mesma configuração já lida por Exposição do
  Cardápio e Avaliação.
- **Interpretação a confirmar em `MediaPorFaixaCalculator`:** o RF13 manda
  calcular a média "considerando apenas os dias com dados". Adotei "dia com
  dados" = dia da janela com pelo menos um check-in naquela refeição e
  campus; nesses dias, uma faixa sem check-in entra na média como zero. A
  alternativa (excluir o dia só daquela faixa quando ela está vazia) daria
  médias maiores e mais instáveis. Vale confirmar com quem escreveu o
  requisito.
- **Detalhes de cálculo que o requisito não fixa:** a suficiência de dados é
  verificada antes de qualquer média, o que garante que a "faixa mais cheia"
  tem média maior que zero e evita divisão por zero no classificador; em
  caso de empate entre faixas mais cheias, proponho destacar todas como pico
  (`ehPico = true`); e o agrupamento em faixas de 15 minutos deve usar o
  horário local (America/Sao_Paulo), não UTC, senão as faixas ficam
  deslocadas em relação aos horários das refeições.
- **Os níveis são relativos à faixa mais cheia, por definição do RF13.**
  Com pouca adesão (L08), a faixa de pico é "longa" mesmo que a média
  absoluta seja de poucos check-ins; a única proteção é a regra de "dados
  insuficientes". Não é um erro do desenho, mas quem for apresentar a
  previsão na interface deve estar ciente dessa limitação.
- **`PrevisaoView` é pública (sem login) e devolve só agregados** — nenhuma
  informação de conta ou de check-in individual sai desse endpoint. Já
  `CheckinView` exige autenticação (RI01).
- **`NivelAgoraService` (RF14) está marcado como Backlog e fica
  deliberadamente incompleto**: o requisito diz que janela de check-ins e
  limiares serão definidos quando o item for priorizado. Por isso ele não
  depende de `ClassificadorNivelFila`; se os limiares finais seguirem a
  mesma lógica relativa do RF13, a classe pode ser reaproveitada.
- **Config de localização:** `LocalizacaoRUConfig` guarda centro e raio por
  RU. O Anexo A exige que o raio do Darcy Ribeiro exclua o Restaurante
  Executivo (RI08); isso só pode ser validado com as coordenadas reais dos
  dois locais, e vale registrar o valor escolhido junto com essa justificativa.

## Nível 4b — Pergunta de saída da fila

```mermaid
classDiagram
  class PerguntaSaidaPendenteView {
    +get(request) Response
  }
  class RespostaSaidaView {
    +post(request) Response
  }
  class DispensaPerguntaSaidaView {
    +post(perguntaId: UUID) Response
  }

  class PerguntaSaidaService {
    +criar(checkin: Checkin, agora: datetime) PerguntaSaida
    +vencidaPendente(conta: Conta, agora: datetime) PerguntaSaida
    +responder(conta: Conta, perguntaId: UUID, resposta: OpcaoRespostaSaida, agora: datetime) RespostaRegistrada
    +dispensar(conta: Conta, perguntaId: UUID, agora: datetime) void
  }
  class PerguntaSaidaRepository {
    +salvar(pergunta: PerguntaSaida) PerguntaSaida
    +buscarDaConta(conta: Conta, perguntaId: UUID) PerguntaSaida
    +vencidaPendenteDaConta(conta: Conta, agora: datetime) PerguntaSaida
    +salvarResposta(resposta: RespostaSaida) RespostaSaida
  }

  class PerguntaSaida {
    +id: UUID
    +checkinId: UUID
    +estado: EstadoPerguntaSaida
    +tentativa: int
    +devidaEm: datetime
    +expiraEm: datetime
    +pontosConcedidosEm: datetime
  }
  class EstadoPerguntaSaida {
    <<enumeration>>
    PENDENTE
    RESPONDIDA
    DISPENSADA
  }
  class RespostaSaida {
    +id: UUID
    +perguntaId: UUID
    +tentativa: int
    +resposta: OpcaoRespostaSaida
    +respondidaEm: datetime
  }
  class OpcaoRespostaSaida {
    <<enumeration>>
    SAI_ATE_5_MIN
    SAI_5_A_10_MIN
    SAI_MAIS_DE_10_MIN
    AINDA_NA_FILA
    DESISTI
  }
  class RespostaRegistrada {
    +pontos: ResultadoPontuacao
    +perguntaDevidaEm: datetime
  }
  class PerguntaPendentePublica {
    +perguntaId: UUID
    +tentativa: int
    +expiraEm: datetime
  }
  class PerguntaExpiradaOuEncerradaError

  class ParametrosFilaConfig {
    <<Anexo A>>
    +primeiraPerguntaMin: int = 15
    +repeticaoMin: int = 10
    +expiracaoMin: int = 60
  }

  class Checkin {
    <<diagrama 4a>>
  }
  class Conta {
    <<Cadastro/Autenticação>>
  }
  class PontuacaoService {
    <<App Gamificação>>
    +registrarContribuicao(conta: Conta, tipo: TipoContribuicao, origemId: UUID, refeicao: RefeicaoRef) ResultadoPontuacao
  }
  class ResultadoPontuacao {
    <<App Gamificação>>
    +total: int
  }

  PerguntaSaidaPendenteView --> PerguntaSaidaService : vencidaPendente()
  PerguntaSaidaPendenteView --> PerguntaPendentePublica : devolve (ou 204)
  RespostaSaidaView --> PerguntaSaidaService : responder()
  DispensaPerguntaSaidaView --> PerguntaSaidaService : dispensar()

  PerguntaSaidaService --> PerguntaSaidaRepository : lê / grava
  PerguntaSaidaService --> ParametrosFilaConfig : lê tempos
  PerguntaSaidaService ..> PerguntaExpiradaOuEncerradaError : lança se expirada ou encerrada
  PerguntaSaidaService --> PontuacaoService : registra contribuição (mesma transação)
  PerguntaSaidaService --> RespostaRegistrada : devolve

  PerguntaSaidaRepository ..> PerguntaSaida : grava/lê
  PerguntaSaidaRepository ..> RespostaSaida : grava
  PerguntaSaida --> EstadoPerguntaSaida : tem
  PerguntaSaida --> Checkin : pertence a (FK)
  RespostaSaida --> PerguntaSaida : responde a (FK)
  RespostaSaida --> OpcaoRespostaSaida : tem
  RespostaRegistrada --> ResultadoPontuacao : tem
  Checkin --> Conta : pertence a (FK)
```

### Notas do diagrama (4b)

- **Uma pergunta por check-in confirmado**, criada no passo 6 do
  `CheckinService` (diagrama 4a), sempre com a hora do servidor:
  `devidaEm` = check-in + 15 min e `expiraEm` = check-in + 60 min (Anexo A).
  Só o autor do check-in a recebe (RI01), em qualquer aparelho em que esteja
  logado (RF21.1), porque o estado fica no servidor.
- **`GET /api/fila/pergunta-pendente/` só devolve pergunta já vencida.** Se
  não houver pergunta `PENDENTE` da conta com `devidaEm ≤ agora < expiraEm`,
  a resposta é **204** (sem corpo). Se houver, é **200** com
  `{perguntaId, tentativa, expiraEm}` (`PerguntaPendentePublica`). Assim o
  PWA não compara o próprio relógio com o do servidor: basta exibir o pop-up
  quando vier 200. A expiração é avaliada na consulta, sem cron: pergunta
  vencida há mais de 60 min do check-in simplesmente deixa de ser devolvida.
- **Quando o PWA consulta (decisão 7):** ao abrir o app, ao voltar ao
  primeiro plano, no horário de `perguntaDevidaEm` (aviso agendado no
  aparelho) e, enquanto houver pergunta não expirada, a cada 2 ou 3 minutos
  com o app aberto. A consulta é invisível; o pop-up só aparece quando a
  pergunta vence. Não há repetição progressiva: a pergunta aparece uma vez e,
  só depois de "Ainda estou na fila", mais uma vez (RF21.2).
- **`POST /api/fila/respostas-saida/`** recebe `{perguntaId, resposta}` e
  grava a `RespostaSaida` com a hora do servidor. Regras (RF21.2, RN07):
  - com `AINDA_NA_FILA` na **primeira** tentativa, a pergunta continua
    `PENDENTE`, com `tentativa = 2` e `devidaEm` = agora + 10 min, desde que
    antes da expiração; a resposta devolve esse novo `perguntaDevidaEm`;
  - qualquer outra resposta, ou qualquer resposta na segunda tentativa,
    encerra a pergunta (`RESPONDIDA`) e devolve `perguntaDevidaEm: null`;
  - pergunta expirada, dispensada ou já respondida devolve `410`
    (`PerguntaExpiradaOuEncerradaError`).

  Resposta (200):

  ```json
  {
    "pontos": {"total": 15, "contribuicao": 15, "avaliacaoLiberada": 0, "bonusSemana": 0},
    "perguntaDevidaEm": "2026-10-27T12:35:00-03:00"
  }
  ```

- **Fechar o pop-up sem responder encerra a pergunta (RF21.2).** O PWA chama
  `POST /api/fila/perguntas-saida/{id}/dispensa/`, e a pergunta passa a
  `DISPENSADA`: não aparece mais em nenhum aparelho. Precisa ser um registro
  no servidor, e não só no aparelho, porque a pergunta vale para todos os
  aparelhos logados. Fechar o pop-up da repetição também encerra. A
  resposta é `204`; se a pergunta já expirou ou foi encerrada em outro
  aparelho, `410`, e o PWA só fecha o pop-up.
- **Pontuação (RN09):** toda resposta chama
  `PontuacaoService.registrarContribuicao(conta, RESPOSTA_SAIDA,
  pergunta.id, refeicao)` na mesma transação, com a `refeicao` do check-in
  da pergunta. Os pontos (15) só são dados uma vez por pergunta, qualquer
  que seja a resposta, inclusive a desistência: o marcador
  `PerguntaSaida.pontosConcedidosEm`, preenchido pela Gamificação, faz a
  segunda resposta (depois de "Ainda estou na fila") voltar com 0. Os pontos
  nunca dependem da resposta escolhida (RI11).
- **O tempo de espera (RN07) e a espera estimada (RN08) não estão neste
  diagrama.** Eles leem `RespostaSaida` e entram com o RF22
  (`TempoEsperaCalculator`, `EsperaEstimadaService`, item 1.2 da lista de
  ajustes).
- **Retenção (RNF07.3):** `RespostaSaida` perde o vínculo com a conta junto
  com o `Checkin`, depois de 4 semanas (pendência do item 1.2 da lista de
  ajustes).
- Estes diagramas são uma **proposta de decomposição inicial**, não uma
  decisão de arquitetura registrada — ajuste-os se a dupla responsável
  encontrar um desenho diferente ao implementar.
