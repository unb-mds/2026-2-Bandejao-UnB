# ADR 0011 — Contadores de gamificação mantidos além da janela de retenção

**Status:** Aceita
**Data:** 2026-10-18 (revisada em 2026-10-23: o ranking passa de mensal a semestral, por campus, e a posição final do semestre anterior passa a ser guardada para a Bandeja de Ouro)
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O RNF07.3 limita a 4 semanas o vínculo dos registros de check-in, de
tentativas e de respostas à pergunta de saída da fila com a conta. Depois
desse prazo, resta só o registro anônimo (campus, refeição, data, faixa e
tempo de espera).

A gamificação da Release 2 (RF24 a RF27: pontos, sequência, patente e
ranking) precisa de memória mais longa que essa janela. A patente é
acumulativa e nunca regride (RN11), e a sequência conta semanas
consecutivas, que podem passar de 4 (RN10). Sem nenhum dado ligado à conta
além da janela, a patente e a sequência reiniciariam a cada 4 semanas, e o
ranking, que é semestral (RN12), não teria como somar os pontos do semestre.

Havia três formas de resolver:

- **(a)** Guardar, ligados à conta, apenas contadores agregados, sem o
  histórico individual de check-ins, respostas e avaliações.
- **(b)** Limitar toda a gamificação à janela de 4 semanas.
- **(c)** Guardar o histórico completo de check-ins ligado à conta.

## Decisão

O sistema passa a guardar, ligados à conta (Usuário), apenas **contadores
agregados**: os pontos totais (que determinam a patente), os pontos do
semestre por campus (usados no ranking), a posição final do semestre
anterior por campus (usada na Bandeja de Ouro), a sequência corrente e a
adesão ao ranking. É a opção (a).

- Os **pontos totais** nunca são zerados: acumulam-se durante toda a vida da
  conta, independentemente do término do semestre letivo, e só mudam por
  ajuste manual da equipe (RN11, L14).
- Os **pontos do semestre por campus** recomeçam do zero a cada semestre
  letivo da UnB, conforme as datas do Anexo A (RN12). O reinício do ranking
  não altera os pontos totais nem a patente.
- A **posição final do semestre anterior** é guardada no fechamento de cada
  semestre letivo, por campus em que o usuário foi elegível, e substituída no
  fechamento seguinte. Só a última fica guardada, sem o histórico de
  semestres. Ela determina a Bandeja de Ouro (30 primeiros de cada campus,
  RN13), que por isso vale apenas durante o semestre seguinte, e só é
  mostrada ao próprio usuário (RF33.3).

- O histórico individual de check-ins, de respostas e de avaliações **não**
  passa a ser mantido por conta além do prazo do RNF07.3.
- Os contadores são removidos junto com a conta (RNF07.4), e a conta sai
  na hora do ranking.
- O RNF07.1, o RNF07.3, o RNF07.4 e o aviso de privacidade são atualizados
  para citar os contadores.

## Consequências

- A patente e a sequência persistem sem reter o histórico de check-ins, e o
  dado pessoal mantido fica reduzido a poucos números.
- Os contadores não podem ser recalculados a partir de registros antigos.
  Um erro de pontuação só se corrige por ajuste manual feito pela equipe
  (acesso direto ao banco, ADR 0004), e uma mudança nos valores de pontos do
  Anexo A vale só daí em diante (L14).
- Para que cada contribuição pontue uma única vez sem um histórico de
  pontos, o banco precisa de um marcador de "pontos já concedidos" nos
  registros que originam a pontuação, ou de uma transação atômica que
  garanta isso.
- Os pontos revelam, de forma aproximada, a frequência de uso do RU. Por
  isso o ranking é opt-in, é separado por campus, é semestral e exibe a
  patente em vez dos pontos (RI12). Pelo mesmo motivo, a posição no ranking
  não é pública: em público aparece só a Bandeja de Ouro, e só para quem
  aderiu ao ranking.
- Guardar o histórico de todas as posições permitiria um distintivo
  permanente ou cumulativo, mas reconstruiria, semestre a semestre, o padrão
  de uso do RU de cada pessoa. Guardar só a última posição atende à
  Bandeja de Ouro com o mínimo de dado pessoal.
- Cada Usuário tem sua pontuação. Quem tem duas contas (L02) tem duas
  pontuações separadas.
- O C4 do banco de dados e o C4 do backend (novo componente de gamificação)
  precisam ser atualizados.

## Alternativas consideradas

**(b) Limitar toda a gamificação à janela de 4 semanas.** Não exigiria mudar
o RNF07.3, mas a patente deixaria de ser acumulativa e a sequência não
passaria de 4 semanas. Isso tira o sentido da progressão e foi descartado.

**(c) Guardar o histórico completo de check-ins ligado à conta.** Permitiria
recalcular qualquer pontuação, mas amplia a retenção de um dado pessoal de
comportamento (o padrão de presença no RU), contraria o princípio de
minimização da LGPD e esvazia o RNF07.3. Foi descartado.

## Relacionadas

- Requisitos: RF24, RF25, RF26, RF27, RF33, RN09, RN10, RN11, RN12, RN13,
  RNF07, RI11, RI12, L02, L14.
- `docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md` (ajuste manual de
  pontuação e remoção de conta).
- `docs/arquitetura/adr/0010-nivel-por-chegadas-com-espera-estimada.md` (outra decisão
  da Release 2 sobre os dados de fila).
