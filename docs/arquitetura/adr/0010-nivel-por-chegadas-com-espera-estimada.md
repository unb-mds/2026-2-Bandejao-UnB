# ADR 0010 — Nível de fila calculado por chegadas, com espera estimada por saída da fila

**Status:** Aceita
**Data:** 2026-10-10
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

A previsão de pico (RF13) mostra o nível de fila esperado em cada faixa de
15 minutos de uma refeição, em quatro níveis (vazia, curta, moderada e
longa). Até aqui, esse nível é calculado **só a partir de chegadas**: a média
de check-ins por faixa nas últimas 4 semanas, e o nível de cada faixa é a
razão entre ela e a faixa mais cheia, com cortes em 25%, 50% e 75%.

Na orientação da professora, surgiu a ideia de perguntar ao usuário, algum
tempo depois do check-in, se ele já saiu da fila (RF21). Isso cria um dado
novo, o **tempo de espera**, que mede o que o usuário realmente quer saber:
quanto tempo vai gastar na fila. O foco declarado da funcionalidade é a
precisão em relação à realidade.

Esse dado novo convive com limites já conhecidos:

- A resposta depende de o usuário voltar ao app, e é menos frequente que o
  check-in (L08). O push que aumentaria as respostas está no Backlog (RF23).
- O nível atual é **relativo**: num dia fraco, a faixa mais cheia pode ser
  "longa" com poucos minutos de espera.
- Quem desiste, quem não responde e quem responde de forma imprecisa fica
  fora do cálculo, e as esperas mais longas são as mais afetadas (L12).
- O RF13 já decidiu não ter valor de reserva: sem dados suficientes, a
  previsão mostra "dados insuficientes".

Havia três formas de usar o tempo de espera:

- **(a)** Manter o nível por chegadas e acrescentar a espera estimada em
  minutos como informação adicional, quando houver dados suficientes.
- **(b)** Calcular o nível pelo tempo de espera, com cortes absolutos em
  minutos, e mostrar "dados insuficientes" nas faixas sem respostas
  suficientes.
- **(c)** Híbrido: usar o tempo de espera quando houver respostas
  suficientes na faixa, e as chegadas quando não houver.

## Decisão

O **nível de fila continua calculado só a partir dos check-ins** (chegadas),
como no RF13, e o **tempo de espera alimenta uma informação à parte, a
espera estimada em minutos** (RF22). É a opção (a).

- O nível de cada faixa não muda com as respostas à pergunta de saída da
  fila. As respostas só alimentam a espera estimada.
- A **espera estimada** de uma faixa é a **mediana** dos tempos de espera da
  faixa nas últimas 4 semanas, para o mesmo dia da semana, campus e
  refeição, arredondada para minutos inteiros.
- Só é exibida quando a faixa tem **ao menos 3 tempos de espera em ao menos
  2 dias distintos**; do contrário, a faixa mostra só o nível.
- Nas faixas com espera estimada, **os minutos aparecem em destaque** e o
  nível aparece como cor ou rótulo, porque o foco é dar ao usuário o tempo
  que ele vai gastar. Um texto de apoio explica que o nível é relativo ao
  movimento do dia e que os minutos são a espera típica observada.
- O tempo de espera é calculado a partir de respostas em **faixas
  fechadas** ("até 5 min", "5 a 10 min"), usando o ponto médio. A resposta
  "há mais de 10 min" não gera tempo de espera. "Ainda estou na fila" sem
  resposta posterior entra como **piso** (a espera real é pelo menos esse
  valor), em vez de ser descartada.

O detalhamento está em RF13, RF21 e RF22.

## Consequências

- O nível continua usando todos os check-ins, que são mais numerosos que as
  respostas. Assim, a previsão resiste à baixa adesão à pergunta de saída da
  fila (L08), e a espera estimada nunca deixa uma faixa sem nível.
- O nível e os minutos podem divergir (por exemplo, nível "longo" com espera
  curta num dia fraco), porque o nível é relativo e a espera é absoluta. O
  texto de apoio na tela é a mitigação. A fragilidade do nível relativo
  continua existindo; esta decisão não a corrige.
- A espera estimada tende a ficar abaixo da realidade (L12): os pisos são
  valores mínimos, e as desistências, os não-respondentes e as respostas
  imprecisas ficam fora do cálculo. A mediana e o aviso na tela reduzem o
  efeito, mas não o eliminam.
- O sistema passa a ter dois cálculos independentes por faixa (nível e
  espera), com mínimos de dados diferentes: o nível exige check-ins em 3
  dias; a espera exige 3 respostas em 2 dias. Os dois ficam no Anexo A e
  devem ser testados separadamente (RNF06).
- Os dados de tempo de espera passam a ser coletados desde a Release 2, mesmo
  que o nível nunca os use. Se, com adesão alta, a equipe quiser migrar o
  nível para minutos absolutos (opção (b)), os dados já existirão, e o custo
  será mudar o cálculo do RF13 e recalibrar os cortes, sem mexer na coleta.
- A decisão depende de a equipe aceitar que a previsão "melhora" mais no que
  mostra (os minutos) do que no que classifica (o nível). Se o objetivo
  passar a ser um nível absoluto, esta ADR deve ser revista.

## Alternativas consideradas

**(b) Nível pelo tempo de espera, com cortes absolutos.** É a opção mais
direta para dar um nível fiel à realidade, e corrigiria o problema do nível
relativo. Não foi adotada porque depende só de quem responde, que é menos
gente que quem faz check-in (L08): muitas faixas ficariam em "dados
insuficientes" no início da operação, e os cortes em minutos exigiriam
calibração sem dados prévios.

**(c) Híbrido.** Cobriria mais faixas que (b), mas misturaria dois critérios
na mesma tela: uma faixa "longa" por chegadas e outra "longa" por minutos
não significariam a mesma coisa para o usuário. Não foi adotada por tornar
o significado do nível ambíguo.

## Relacionadas

- Requisitos: RF11, RF13, RF21, RF22, RI05, L08, L12.
- `docs/adr/0009-deteccao-de-campus-no-aparelho.md` (outra decisão da
  Release 2, sobre o uso da localização).
