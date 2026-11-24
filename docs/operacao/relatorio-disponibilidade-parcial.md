# Relatório parcial de disponibilidade (BD-09)

Meta (RNF02): **95%** das 7h às 19h30, nos dias com refeição servida. A meta é
avaliada no **período**: equivale, em média, a 37,5 minutos de queda por dia de
refeição (de 750 minutos). Método de cálculo em
[monitor de disponibilidade](operacao/monitor-disponibilidade.md). A medida oficial é o
monitor da API; o do site é diagnóstico.

**Situação:** modelo pronto, aguardando os dias de refeição. Os campos
`_preencher_` saem do painel do UptimeRobot. Quando o relatório for preenchido,
troque esta linha pela data de fechamento.

## Metadados

- Data de fechamento: `_preencher_`.
- Quem fechou: `_preencher_`.
- Monitores usados: `_preencher_` (nomes dos monitores no painel).
- Fuso da conta do UptimeRobot (*Account details → Timezone*): `_preencher_`
  (deve ser `America/Sao_Paulo`, UTC−3; confira no fechamento).

## Período

- Início da coleta: 21/11/2026. Os monitores foram criados à noite, então esse
  dia é incompleto e não entra nos dias de refeição.
- Período do relatório: `_preencher_` a `_preencher_`.
- Dias de refeição no período: `_preencher_` (lista das datas contadas).
- Minutos de janela no período: `_preencher_` (750 × dias de refeição).

### Critério dos dias de refeição

- Vale o **RU do campus Darcy Ribeiro** (o mesmo da palavra do monitor): um dia
  é de refeição se esse RU serve refeição nele, segundo o calendário do RU da
  UnB. O calendário decide, sem excluir o fim de semana por regra.
- Ficam de fora os dias em que o RU do Darcy não serve (feriados e recessos,
  por exemplo), mesmo com a coleta ligada, e os dias incompletos de coleta (o
  21/11). O Darcy serve aos domingos (#229): **domingo com refeição conta**.
- Uma falha do leitor do PDF **não** tira o dia da conta: o sistema segue no ar
  com o último cardápio.
- A lista das datas contadas fica anotada em "Dias de refeição no período".

### O que conta e o que não conta como queda

- **Conta:** qualquer incidente real do monitor da API dentro da janela,
  inclusive o causado por deploy planejado (o usuário viu o serviço fora).
- **Não conta:** falso positivo do monitor, confirmado (o serviço respondia
  normalmente por outro meio) e queda do próprio UptimeRobot. Esses entram na
  tabela de incidentes, marcados como "não conta", com o motivo.

## Resumo

| Monitor | Papel | Minutos fora do ar na janela | Disponibilidade no período (%) | Meta de 95% |
|---|---|---|---|---|
| API (`/api/campi/`, palavra `Darcy Ribeiro`) | oficial | `_preencher_` | `_preencher_` | `_atingida / não atingida_` |
| Site (`bandejaounb.com.br`) | diagnóstico | `_preencher_` | `_preencher_` | não se aplica |

## Por dia de refeição

A coluna de disponibilidade do dia é informativa: a meta é avaliada no
período, e um dia ruim não reprova sozinho.

| Data | API: min fora na janela | Site (diagnóstico): min fora | Disponibilidade do dia, pela API (%) |
|---|---|---|---|
| `_preencher_` | `_preencher_` | `_preencher_` | `_preencher_` |

## Incidentes

| Monitor | Início | Fim | Duração | No período? | Conta? | Min na janela (que contam) | Motivo | Ação |
|---|---|---|---|---|---|---|---|---|
| `_preencher_` | `_preencher_` | `_preencher_` | `_preencher_` | `_sim / não_` | `_sim / não_` | `_preencher_` | `_preencher_` | `_preencher_` |

"Min na janela (que contam)" é o número que entra na conta: só os minutos
entre 7h00 e 19h30 de dias de refeição, e **0** se `Conta?` for "não". Um
incidente que atravessa os limites da janela conta só a parte de dentro.

Sem incidentes no período: apague a linha `_preencher_` e escreva "nenhum
incidente registrado".

## Leitura

- `_preencher_`: o que explica os incidentes e se a meta foi cumprida.
- Este é um relatório **parcial**: não cobre o semestre inteiro, e um período
  curto sem queda não prova a meta. A coleta segue em andamento.
- A checagem de 5 em 5 minutos pode deixar passar quedas mais curtas.

## Evidência

- Print do painel do período, anexado ao relatório. **Corte o e-mail da
  conta** antes de anexar: o repositório é público.
- Exportação do log de incidentes (CSV) feita **no dia do fechamento**, porque
  o histórico do plano gratuito é limitado. Onde o arquivo ficou:
  `_preencher_`.
- Para não perder dado, guarde o log de incidentes **uma vez por mês** (CSV,
  ou print da lista de incidentes se o plano gratuito não exportar). Plano B
  sem CSV: copie cada incidente para a tabela do relatório no mesmo dia em
  que ele acontece.

## Como preencher

1. Em *Account details → Timezone* do UptimeRobot, confira que a conta está em
   `America/Sao_Paulo` (UTC−3) e anote isso nos metadados.
2. No painel, abra cada monitor e consulte o log de incidentes do período
   (início, fim e duração de cada um). Exporte o CSV e anote onde ficou.
3. Para cada incidente do monitor da API com `Conta? = sim`, some os minutos
   dentro de 7h00 a 19h30 (horário de Brasília) de cada dia de refeição que ele
   atravessa, cortando nos limites da janela, e anote em "Min na janela (que
   contam)". Some a coluna e preencha o resumo e a tabela por dia. O monitor do
   site fica como diagnóstico. Um incidente ainda aberto termina na hora do
   fechamento.
4. Calcule `(1 − minutos fora ÷ (750 × dias de refeição)) × 100`, em %. A meta
   é atingida se os minutos que contam forem **no máximo 37,5 × dias de
   refeição** (compare por essa regra, sem arredondar o percentual).
5. Anexe o print do painel do período, para a conferência.
6. Preencha os metadados e troque a linha "Situação" no topo.
