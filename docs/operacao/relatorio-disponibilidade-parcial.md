# Relatório parcial de disponibilidade (BD-09)

Meta (RNF02): **95%** das 7h às 19h30, nos dias com refeição servida. A meta é
avaliada no **período**: equivale, em média, a 37,5 minutos de queda por dia de
refeição (de 750 minutos). Método de cálculo em
[monitor de disponibilidade](monitor-disponibilidade.md). A medida oficial é o
monitor da API; o do site é diagnóstico.

**Situação:** modelo pronto, aguardando os dias de refeição. Os campos
`_preencher_` saem do painel do UptimeRobot. Quando o relatório for preenchido,
troque esta linha pela data de fechamento.

## Metadados

- Data de fechamento: `_preencher_`.
- Quem fechou: `_preencher_`.
- Monitores usados: `_preencher_` (oficial: API `Keyword on
  bandejaounb.com.br/api/campi/`; diagnóstico: site `bandejaounb.com.br`).
- Fuso da conta do UptimeRobot (*Account details → Timezone*): `_preencher_`
  (deve ser `America/Sao_Paulo`, UTC−3; conferido em 23/11/2026, quando
  estava em `Sao Paulo (GMT-03:00)`; confira de novo no fechamento).

## Período

- Início da coleta: 21/11/2026 (monitores criados à noite, num sábado).
- Período do relatório: `_preencher_` a `_preencher_`.
- Dias de refeição no período: `_preencher_` (lista das datas contadas).
- Minutos de janela no período: `_preencher_` (750 × dias de refeição).

### Critério dos dias de refeição

- São os dias em que o RU serve refeição, segundo o calendário do RU da UnB
  (os dias com cardápio publicado no sistema para o campus).
- Ficam de fora os sábados, domingos, feriados e recessos em que o RU não
  serve, mesmo com a coleta ligada. Por isso o dia 21/11 (sábado) não conta.
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

| Monitor | Início | Fim | Duração | No período? | Dentro da janela? | Conta? | Motivo | Ação |
|---|---|---|---|---|---|---|---|---|
| `_preencher_` | `_preencher_` | `_preencher_` | `_preencher_` | `_sim / não_` | `_sim / não_` | `_sim / não_` | `_preencher_` | `_preencher_` |

Sem incidentes no período: escrever "nenhum incidente registrado" e manter a
tabela vazia.

## Leitura

- `_preencher_`: o que explica os incidentes e se a meta foi cumprida.
- Este é um relatório **parcial**: não cobre o semestre inteiro, e um período
  curto sem queda não prova a meta. A coleta segue em andamento.
- A checagem de 5 em 5 minutos pode deixar passar quedas mais curtas.

## Evidência

- Print do painel do período, anexado ao relatório.
- Exportação do log de incidentes (CSV) feita **no dia do fechamento**, porque
  o histórico do plano gratuito é limitado. Onde o arquivo ficou:
  `_preencher_`.

## Como preencher

1. Em *Account details → Timezone* do UptimeRobot, confira que a conta está em
   `America/Sao_Paulo` (UTC−3) e anote isso nos metadados.
2. No painel, abra cada monitor e consulte o log de incidentes do período
   (início, fim e duração de cada um). Exporte o CSV e anote onde ficou.
3. Some os minutos do monitor da API que caem entre 7h00 e 19h30 de dias de
   refeição (horário de Brasília) e preencha as tabelas. O monitor do site
   fica como diagnóstico.
4. Calcule `(1 − minutos fora ÷ (750 × dias de refeição)) × 100`, em %.
5. Anexe o print do painel do período, para a conferência.
6. Preencha os metadados e troque a linha "Situação" no topo.
