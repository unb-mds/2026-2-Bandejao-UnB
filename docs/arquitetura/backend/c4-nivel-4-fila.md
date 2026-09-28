# Arquitetura C4 — Nível 4 (Fila e Previsão de Pico) — Bandejão

> Detalha, em diagrama de classes, o componente **Fila**, desenhado no
> Nível 3 do backend (ver `c4-nivel-3-backend.md`). Cobre o Épico Fila e
> Previsão de Pico: check-in no RU (RF11), confirmação por GPS (RF12),
> previsão de pico por faixa de horário (RF13) e, como item de Backlog,
> nível de fila "agora" (RF14).
>
> Todo o épico é **Release 2 / Backlog**: nada aqui faz parte do MVP. O
> diagrama existe para que a decomposição já esteja pensada quando a
> Release 2 começar.
>
> Como nos outros Níveis 4, este componente só **lê** models de outros
> componentes (`Conta`, do Cadastro/Autenticação) por chave estrangeira, sem
> chamada entre componentes (ver nota do Nível 3).

## Nível 4 — Diagrama de Classes da Fila

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
    +registrar(conta: Conta, campus: Campus, tipoRefeicao: str, coordenadas: Coordenadas, agora: datetime) Checkin
  }
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
    +id: UUID
  }

  CheckinView --> CheckinService : registrar()
  PrevisaoView --> PrevisaoService : calcular()
  NivelAgoraView --> NivelAgoraService : calcular()

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

### Notas do diagrama

- **`Coordenadas` nunca é persistida nem registrada em log** (RI09, RF12). O
  objeto nasce da requisição, é usado só por `ConfirmacaoLocalizacaoService`
  para comparar a distância com o raio do RU e descartado; nenhum model
  (`Checkin`, `TentativaCheckin`) tem campo de latitude/longitude. Na
  implementação, isso vale também para o log de acesso do servidor: o corpo
  da requisição de check-in não deve ser gravado.
- **A ordem das validações do `CheckinService` é deliberada**: horário,
  depois duplicidade, depois localização — do mais barato ao mais caro, e de
  modo que uma tentativa que já seria rejeitada por outro motivo não
  dependa do GPS. Como a conferência de localização é o passo que o RF12
  descreve como "cada tentativa registra usuário, campus, refeição, data/hora
  e resultado", desenhei `TentativaCheckin` como gravada a partir dessa
  etapa (confirmada ou rejeitada). **Ponto para alinhar:** o texto do RF12
  não deixa claro se tentativas rejeitadas por horário ou por duplicidade
  também devem gerar `TentativaCheckin`; na leitura literal, não.
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
- Este diagrama é uma **proposta de decomposição inicial**, não uma decisão
  de arquitetura registrada — ajuste-o se a dupla responsável encontrar um
  desenho diferente ao implementar.
