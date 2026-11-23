# Teste de carga do cardápio e da previsão (BD-14)

**Issue:** [#184](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/184) · **Requisito:** RNF01 · **Data:** 22/11/2026

> **Resultado: meta não atingida com 2.000 usuários simultâneos.** O p95
> ficou dentro de 3 s com 500 usuários em todas as medições. Com 1.000, ficou
> no limite: passou em duas varreduras (1,7 e 1,8 s) e falhou na terceira
> (3,2 s). Com 1.500 e 2.000, passou de 3 s sempre. Nenhum pedido falhou em
> nenhuma rodada. Pelo backlog (BD-14), com a meta
> não atingida, o DOC é avisado para rever o número do RNF01.

## Meta

> O sistema deve responder a requisições de visualização de cardápio (e, na
> Release 2, de previsão de pico) em até **3 segundos**, em condições normais
> de operação (até **2.000 usuários simultâneos**), medido do lado do servidor
> em pelo menos 95% das requisições.
>
> — RNF01, Documento de Requisitos

## Resultado

Três varreduras, em runners diferentes, com uma rodada de 5 minutos
por número de usuários e rampa de 50 usuários por segundo. O p95 é o mesmo nos
dois endpoints, porque o tempo é dominado pela fila (ver "Leitura"). A rodada
de 2.000 usuários também foi feita antes, sozinha, e deu 6,9 s de p95.

| Usuários simultâneos | Pedidos/s (1ª / 2ª / 3ª) | p95 (1ª / 2ª / 3ª) | Falhas | Meta |
|---:|---:|---:|---:|---|
| 500 | 98 / 98 / 98 | 0,08 / 0,16 / 0,19 s | 0 | ✅ |
| 1.000 | 148 / 151 / 124 | 1,8 / 1,7 / 3,2 s | 0 | ⚠️ no limite |
| 1.500 | 181 / 120 / 145 | 4,2 / 7,5 / 5,2 s | 0 | ❌ |
| 2.000 | 172 / 136 / 128 | 6,4 / 9,6 / 11 s | 0 | ❌ |

A 3ª varredura já conta como falha a resposta 200 sem o conteúdo completo
(revisão do PR #244), e mesmo assim deu 0 falhas: as respostas medidas eram
as completas.

Execuções no GitHub Actions:
[1ª varredura](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45095023478),
[2ª varredura](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45099315859),
[3ª varredura](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45111606717)
(as duas no PR #244) e
[primeira rodada de 2.000](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45093053733).
O CSV completo do Locust fica nos artefatos `resultado-carga-*` de cada execução.

### Leitura

- **O servidor satura entre 120 e 180 pedidos por segundo**, conforme o
  runner. Com 1.000 usuários, a demanda é de uns 170 pedidos por segundo:
  num runner mais lento, já passa da capacidade. Acima disso, os pedidos esperam na fila dos 3 workers do Gunicorn.
  Por isso o tempo sobe junto nos dois endpoints, e a vazão para de crescer
  (ou até cai) entre 1.500 e 2.000 usuários.
- **A causa não é consulta lenta.** Por pedido, o cardápio faz 8 consultas
  simples e a previsão faz 2, usando os índices conferidos na BD-10
  (`docs/arquitetura/banco-de-dados/indices-bd10.md`). A contagem foi feita
  uma vez, com o `CaptureQueriesContext` do Django num pedido de cada
  endpoint depois do `carga.dados`, e não fica travada em teste (o número é
  da BE-11 e da BE-15). Pela vazão máxima, cada
  pedido ocupa um worker por algo entre 17 e 25 ms (3 workers ÷ 180 ou 120
  pedidos/s).
- **A meta vale com folga até 500 usuários simultâneos** (p95 abaixo de
  0,2 s nas três varreduras). **Com 1.000, fica no limite**: passou em duas e
  falhou na terceira (3,2 s). Com 1.500 ou mais, falha sempre, no cenário
  abaixo.

## Cenário

| Item | Valor |
|---|---|
| Endpoints | `GET /api/cardapio/?campus=` e `GET /api/fila/previsao/?campus=&refeicao=`, sem login |
| Mistura | 3 pedidos de cardápio para 1 de previsão (o cardápio é a tela de entrada do PWA) |
| Comportamento de cada usuário | Um pedido a cada 3 a 7 s (o tempo de ler a tela), sorteando campus e refeição |
| Dados | Semana publicada nos 5 campi (café, almoço e jantar todos os dias, 4 categorias por refeição, cada uma com 3 pratos, cada prato com 2 marcadores) e 4 semanas de check-ins, 200 por campus, refeição e dia (84.000 no total), sem conta |
| Servidor | Gunicorn como em produção (`entrypoint.sh`: 3 workers, timeout de 30 s), `DEBUG` desligado, MySQL 8.4 |
| Gerador | Locust 2.46.7, com 2 processos, na mesma máquina |
| Medida | Tempo de resposta no Locust, por `localhost`, sem rede no meio: na prática, o tempo do lado do servidor, com a fila incluída |

As respostas medidas são as completas: o teste confere antes de começar que o
cardápio vem `publicado` e a previsão vem `disponivel`, e não as respostas
vazias, que são mais leves.

### Premissa que muda o número

O "usuário simultâneo" foi modelado como alguém com o app aberto que faz um
pedido a cada 3 a 7 s. Com 2.000 usuários, isso dá cerca de 400 pedidos por
segundo. Se a equipe definir que o usuário fica mais tempo em cada tela, o
mesmo servidor aguenta mais usuários. A premissa não foi ajustada para passar
no teste. Para medir outra, use `CARGA_ESPERA_MIN` e `CARGA_ESPERA_MAX` (ver
"Como rodar").

## Limites da medição

- **Máquina diferente da produção.** O runner do GitHub tem 4 vCPUs e divide
  a máquina entre o Locust, o Gunicorn e o MySQL. A VM de produção (B2as_v2)
  tem 2 vCPUs e divide com o MySQL e o Caddy. Em produção, a capacidade tende
  a ser **menor** que a medida aqui.
- **Sem o Caddy e sem o HTTPS.** O teste vai direto no Gunicorn.
- **Sem o cache do navegador.** O cardápio responde com `ETag`, e o PWA pode
  receber `304` em pedidos repetidos, o que alivia o servidor. O teste pede a
  resposta completa toda vez.
- **Sem o log de acesso do Gunicorn**, que a produção tem (`entrypoint.sh`).
  Escrever uma linha por pedido custa um pouco em produção; o teste deixou de
  fora para não encher o disco do runner.
- **A rampa entra nas estatísticas.** Com 2.000 usuários a 50 por segundo,
  são uns 40 s de subida dentro dos 5 minutos, com menos usuários que o
  alvo, o que puxa o p95 para baixo. Não muda a conclusão, porque o p95 já
  passa da meta com a rampa dentro.
- **Respostas vazias contam como falha.** Desde a revisão do PR #244, um
  cardápio `nao_publicado` ou uma previsão `dados_insuficientes` (mais
  baratos) contam como falha no Locust. As medições acima são de antes disso,
  mas o teste de fumaça do workflow já conferia `publicado` e `disponivel`
  antes da carga.
- O teste **não roda contra a produção**. 2.000 usuários derrubariam o
  serviço de quem está usando. O `carga.dados` só grava com
  `CARGA_CONFIRMO_BANCO_DESCARTAVEL=1`, que só o workflow define, e se recusa
  a popular um banco que já tenha check-in, refeição ou fonte de cardápio. O
  pacote também fica fora da imagem do backend.

## O que pode melhorar a capacidade

Não faz parte da BD-14; fica como sugestão para a equipe decidir.

- **Cache das respostas.** O cardápio só muda quando o Leitor roda (de 3 em
  3 horas), e a previsão usa só dias que já passaram, então muda uma vez por
  dia. Guardar as duas respostas em cache por alguns minutos deve multiplicar
  a vazão. Isso mexe no código da BE-11 e da BE-15 e precisa ser medido de
  novo com este mesmo teste.
- **Mais CPU na VM.** Com mais vCPUs, dá para subir o número de workers do
  Gunicorn (regra 2 × CPUs + 1). Isso tem custo no crédito da Azure (ADR
  0012).

## Como rodar

O teste está no pacote `backend/carga/`, com os testes em
`backend/tests/test_carga_bd14.py`:

| Arquivo | O que faz |
|---|---|
| `dados.py` | Popula um banco vazio com o volume do teste (exige a confirmação e recusa banco com check-in ou cardápio) |
| `cenario.py` | Os pedidos de cada usuário simulado e a conferência do corpo das respostas |
| `locustfile.py` | Os usuários simulados, para o Locust |
| `avaliar.py` | Lê o CSV do Locust e compara o p95 e as falhas com a meta |

**No GitHub Actions** (é o jeito recomendado). O workflow
`.github/workflows/carga.yml` roda à mão, em Actions > Teste de carga > Run
workflow, com a lista de usuários de cada rodada (padrão
`[500, 1000, 1500, 2000]`) e a duração. Ele também roda sozinho no PR para a
`develop` quando um desses arquivos muda. Fica fora do push e do PR de
release (`develop` → `main`), que publica o site.

No CI, todas as rodadas são **informativas**: o desempenho não derruba o job,
e o veredito ("Aprovado" ou "Reprovado") aparece no resumo do job. A exceção
é uma carga que não mediu (um endpoint sem requisição, ou mais da metade com
falha): isso é teste quebrado, e o job falha. O log de erros do Gunicorn vai
para o artefato. Com a meta não atingida,
um X permanente no PR deixaria de ser sinal. O código de saída do veredito
continua no `carga.avaliar` sem o `--informativo` (ver "Na mão").

**Na mão**, numa máquina Linux com MySQL e um banco vazio:

```bash
cd backend
pip install -r requirements-prod.txt -r requirements-carga.txt
python manage.py migrate
python manage.py loaddata campi marcadores
CARGA_CONFIRMO_BANCO_DESCARTAVEL=1 CARGA_CHECKINS=200 \
  python manage.py shell -c "from carga.dados import main; main()"
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 30 &
locust -f carga/locustfile.py --headless --host http://127.0.0.1:8000 \
  -u 2000 -r 50 -t 5m --processes 2 --csv resultado/carga --only-summary
USUARIOS=2000 python -m carga.avaliar resultado/carga_stats.csv
```
