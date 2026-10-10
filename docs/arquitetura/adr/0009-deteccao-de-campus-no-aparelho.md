# ADR 0009 — Detecção de campus feita no aparelho

**Status:** Aceita, com pontos em aberto (valores dos parâmetros de GPS e contrato da API)
**Data:** 2026-10-10
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

Na Release 2, o sistema usa a localização do dispositivo para dois fins
distintos:

- **Detectar o campus** em que a pessoa está, a cada abertura do app, e abrir
  a tela desse campus já com as informações dele, para reduzir os toques até
  o cardápio (RF20). Vale para o Visitante e para o usuário logado, e a
  detecção ocorre com frequência: a cada abertura do app e a cada volta ao
  primeiro plano depois de 30 minutos parado.
- **Confirmar o check-in**, que só é aceito se a pessoa estiver nas
  imediações do RU (RF12). Aqui a conferência precisa ser feita onde o
  usuário não consegue adulterá-la.

O RI09 proíbe armazenar as coordenadas do usuário, e o RNF07 exige que os
dados sejam coletados só para as finalidades declaradas. Como a detecção de
campus é muito mais frequente que o check-in e vale também para quem não
está logado, o modo como ela é feita define quanto dado de localização
trafega para o servidor. O RNF03 e o RNF01 também pesam: o cardápio deve
abrir sem esperar a leitura do GPS.

Havia duas formas de detectar o campus:

- **No servidor:** o PWA envia as coordenadas, e o backend responde com o
  campus e as informações dele.
- **No aparelho:** o PWA recebe do backend as coordenadas e o raio de cada
  campus, compara com a posição lida pelo navegador e pede ao backend apenas
  o cardápio do campus escolhido.

## Decisão

A detecção de campus é feita **no aparelho**, pelo PWA.

- O backend publica, para o PWA, as coordenadas e o **raio de detecção** de
  cada campus (Anexo A do Documento de Requisitos). O PWA lê a posição pelo
  navegador, compara com esses valores e decide o campus detectado.
- O backend recebe **apenas o identificador do campus**, nas requisições de
  cardápio, avaliações e previsão. As coordenadas do usuário nunca saem do
  aparelho na detecção (RI09).
- O **raio de detecção de campus** e o **raio de confirmação do check-in**
  são parâmetros distintos: o primeiro cobre o campus inteiro e é grande; o
  segundo cobre as imediações do RU e é pequeno.
- A **conferência do check-in continua no servidor** (RF12): o PWA envia as
  coordenadas apenas nesse momento, o backend confere e as descarta. A
  decisão não muda isso.
- A hierarquia de qual campus exibir (escolha manual, campus detectado,
  campus lembrado, seletor) e o campus lembrado ficam no PWA, como estado do
  aparelho (RF07, RF20), no mesmo espírito da preferência de filtros da
  ADR 0005.
- O tempo limite da leitura, a precisão mínima e a idade máxima da posição
  (Anexo A) valem para a detecção: leitura fora desses limites equivale a
  "campus não detectado", e vale o campus lembrado.

## Consequências

- Atende ao RI09 e ao RNF07 com folga na parte mais frequente do uso: o
  servidor não vê a localização de quem apenas abre o cardápio, inclusive
  de quem não está logado. O aviso de privacidade (RF19) pode afirmar que,
  na detecção, as coordenadas não saem do aparelho.
- O PWA não precisa esperar uma ida e volta ao servidor para decidir o
  campus, o que ajuda a abrir o cardápio imediatamente (RNF03).
- A conta de distância entre dois pontos passa a existir em dois lugares: no
  PWA (detecção) e no backend (conferência do check-in). As duas precisam
  concordar, e a duplicação deve ser coberta por testes em cada lado, já que
  a detecção e o check-in estão entre os módulos críticos do RNF06.
- Como a decisão do campus é tomada no aparelho, o servidor não confere o
  campus informado. Um usuário mal-intencionado poderia pedir as informações
  de outro campus, mas isso não tem consequência de segurança: são dados
  públicos. A confirmação de que a pessoa está no RU continua sendo feita
  pelo servidor no check-in.
- O contrato entre PWA e backend precisa incluir a publicação das
  coordenadas e dos raios de detecção por campus. A forma exata (endpoint ou
  campo em outra resposta) deve ser combinada entre as duplas das duas
  frentes, como já ocorre com o contrato dos filtros (ADR 0005).
- Como os raios vêm do backend, ajustá-los depois de testes em campo não
  exige nova versão do PWA. Os valores ainda não estão definidos e dependem
  de teste em campo, em especial no Darcy Ribeiro (L05).
- O erro de GPS não costuma ser um risco para a detecção, já que os campi
  ficam a distâncias grandes uns dos outros, e o raio de detecção de cada um
  deve ficar bem abaixo da metade da distância até o campus mais próximo. O
  caso mais provável é a pessoa não ser detectada (por exemplo, em um canto
  distante do campus), e o fallback para o campus lembrado cobre isso.
- Reverter a decisão (passar a detectar no servidor) exigiria um endpoint que
  receba coordenadas, a revisão do RI09 e do aviso de privacidade (RF19) e a
  remoção da lógica do PWA. O custo é moderado, mas reabriria a questão de
  privacidade para o Visitante.

## Alternativa considerada

**Detecção no servidor.** Concentraria toda a regra no backend, sem
duplicar a conta de distância, e seguiria o padrão da ADR 0005. Não foi
adotada porque faria o servidor receber as coordenadas a cada abertura do
app, inclusive de quem não está logado, o que ampliaria o tratamento de
localização sem necessidade: para escolher um campus, o servidor só precisa
saber qual foi escolhido.

## Pontos em aberto

- **Valores dos parâmetros de GPS** (coordenadas e raio de detecção por
  campus, precisão mínima e idade máxima da posição): a definir pela equipe,
  com teste em campo (Anexo A).
- **Forma de publicação** das coordenadas e dos raios pelo backend: a
  combinar entre as duplas das duas frentes.

## Relacionadas

- Requisitos: RF07, RF12, RF19, RF20, RI09, RNF01, RNF03, RNF06, RNF07, L05.
- `docs/adr/0005-filtros-de-marcador-e-dieta-no-backend.md` (decisão
  oposta quanto ao local da lógica, mantendo a preferência no aparelho).
