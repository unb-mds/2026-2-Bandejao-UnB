# Relatório parcial de disponibilidade (BD-09)

Meta (RNF02): **95%** das 7h às 19h30, nos dias com refeição servida, ou seja,
no máximo 37,5 minutos fora do ar por dia (de 750 minutos). Método de cálculo
em [monitor de disponibilidade](monitor-disponibilidade.md).

**Situação:** modelo pronto, aguardando os dias de refeição. Os campos
`_preencher_` saem do painel do UptimeRobot.

## Período

- Início da coleta: 21/11/2026 (monitores criados à noite).
- Período do relatório: `_preencher_` a `_preencher_`.
- Dias de refeição no período: `_preencher_`.
- Minutos de janela no período: `_preencher_` (750 × dias de refeição).

## Resumo por monitor

| Monitor | Minutos fora do ar na janela | Disponibilidade na janela | Meta de 95% |
|---|---|---|---|
| Site (`bandejaounb.com.br`) | `_preencher_` | `_preencher_` | `_atingida / não atingida_` |
| API (`/api/campi/`, palavra `Darcy Ribeiro`) | `_preencher_` | `_preencher_` | `_atingida / não atingida_` |

## Por dia de refeição

| Data | Site: min fora | API: min fora | Disponibilidade do dia (pior dos dois) |
|---|---|---|---|
| `_preencher_` | `_preencher_` | `_preencher_` | `_preencher_` |

## Incidentes

| Monitor | Início | Fim | Duração | Dentro da janela? | Motivo | Ação |
|---|---|---|---|---|---|---|
| `_preencher_` | `_preencher_` | `_preencher_` | `_preencher_` | `_sim / não_` | `_preencher_` | `_preencher_` |

Sem incidentes no período: escrever "nenhum incidente registrado" e manter a
tabela vazia.

## Leitura

- `_preencher_`: o que explica os incidentes e se a meta foi cumprida.
- Este é um relatório **parcial**: não cobre o semestre inteiro, e um período
  curto sem queda não prova a meta. A coleta segue em andamento.
- A checagem de 5 em 5 minutos pode deixar passar quedas mais curtas.

## Como preencher

1. No painel do UptimeRobot, abra cada monitor e consulte o log de incidentes
   do período (início, fim e duração de cada um).
2. Some os minutos que caem entre 7h00 e 19h30 de dias de refeição (horário de
   Brasília) e preencha as tabelas.
3. Calcule `1 − minutos fora ÷ (750 × dias de refeição)`.
4. Anexe o print do painel do período, para a conferência.
