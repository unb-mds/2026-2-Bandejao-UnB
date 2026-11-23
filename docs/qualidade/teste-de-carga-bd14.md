# Teste de carga do cardápio e da previsão (BD-14)

**Issue:** [#184](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/184) · **Requisito:** RNF01 · **Data:** 22/11/2026

> **Resultado: meta não atingida com 2.000 usuários simultâneos.** O p95
> ficou dentro de 3 s até 1.000 usuários. Com 1.500 e 2.000, passou de 3 s.
> Nenhum pedido falhou em nenhuma rodada. Pelo backlog (BD-14), com a meta
> não atingida, o DOC é avisado para rever o número do RNF01.

## Meta

> O sistema deve responder a requisições de visualização de cardápio (e, na
> Release 2, de previsão de pico) em até **3 segundos**, em condições normais
> de operação (até **2.000 usuários simultâneos**), medido do lado do servidor
> em pelo menos 95% das requisições.
>
> — RNF01, Documento de Requisitos

## Resultado

Duas varreduras, em dias de runner diferentes, com uma rodada de 5 minutos
por número de usuários e rampa de 50 usuários por segundo. O p95 é o mesmo nos
dois endpoints, porque o tempo é dominado pela fila (ver "Leitura"). A rodada
de 2.000 usuários também foi feita antes, sozinha, e deu 6,9 s de p95.

| Usuários simultâneos | Pedidos/s (1ª / 2ª) | p95 (1ª / 2ª) | Falhas | Meta |
|---:|---:|---:|---:|---|
| 500 | 98 / 98 | 0,08 s / 0,16 s | 0 | ✅ |
| 1.000 | 148 / 151 | 1,8 s / 1,7 s | 0 | ✅ |
| 1.500 | 181 / 120 | 4,2 s / 7,5 s | 0 | ❌ |
| 2.000 | 172 / 136 | 6,4 s / 9,6 s | 0 | ❌ |

Execuções no GitHub Actions:
[1ª varredura](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45095023478),
[2ª varredura](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45099315859)
(no PR #244) e
[primeira rodada de 2.000](https://github.com/unb-mds/2026-2-Bandejao-UnB/actions/runs/45093053733).
O CSV completo do Locust fica nos artefatos `resultado-carga-*` de cada execução.

### Leitura

- **O servidor satura entre 120 e 180 pedidos por segundo**, conforme o
  runner. Acima disso, os pedidos esperam na fila dos 3 workers do Gunicorn.
  Por isso o tempo sobe junto nos dois endpoints, e a vazão para de crescer
  (ou até cai) entre 1.500 e 2.000 usuários.
- **A causa não é consulta lenta.** Por pedido, o cardápio faz 8 consultas
  simples e a previsão faz 2, usando os índices conferidos na BD-10
  (`docs/arquitetura/banco-de-dados/indices-bd10.md`). Pela vazão máxima, cada
  pedido ocupa um worker por algo entre 17 e 25 ms (3 workers ÷ 180 ou 120
  pedidos/s).
- **A meta vale com 1.000 usuários simultâneos** nas duas varreduras (p95 de
  1,7 a 1,8 s) e falha com 1.500, no cenário abaixo. A variação entre as
  varreduras mostra que a margem acima de 1.000 é pequena.

## Cenário

| Item | Valor |
|---|---|
| Endpoints | `GET /api/cardapio/?campus=` e `GET /api/fila/previsao/?campus=&refeicao=`, sem login |
| Mistura | 3 pedidos de cardápio para 1 de previsão (o cardápio é a tela de entrada do PWA) |
| Comportamento de cada usuário | Um pedido a cada 3 a 7 s (o tempo de ler a tela), sorteando campus e refeição |
| Dados | Semana publicada nos 5 campi (café, almoço e jantar todos os dias, 4 categorias e 3 pratos com marcadores por refeição) e 4 semanas de check-ins, 200 por campus, refeição e dia (84.000 no total), sem conta |
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
- O teste **não roda contra a produção**. 2.000 usuários derrubariam o
  serviço de quem está usando, e o `carga.dados` se recusa a popular um banco
  que já tem check-ins.

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
| `dados.py` | Popula um banco vazio com o volume do teste (recusa banco com check-ins) |
| `cenario.py` | Os pedidos de cada usuário simulado |
| `locustfile.py` | Os usuários simulados, para o Locust |
| `avaliar.py` | Lê o CSV do Locust e compara o p95 e as falhas com a meta |

**No GitHub Actions** (é o jeito recomendado). O workflow
`.github/workflows/carga.yml` roda sozinho quando um desses arquivos muda,
no push e no PR. Ele também pode ser disparado à mão em Actions > Teste de
carga > Run workflow, com a lista de usuários de cada rodada (padrão
`[500, 1000, 1500, 2000]`) e a duração. Só a rodada de 2.000 decide o
veredito; as outras são informativas. O resultado aparece no resumo do job.

**Na mão**, numa máquina Linux com MySQL e um banco vazio:

```bash
cd backend
pip install -r requirements-prod.txt -r requirements-carga.txt
python manage.py migrate
python manage.py loaddata campi marcadores
CARGA_CHECKINS=200 python manage.py shell -c "from carga.dados import main; main()"
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 30 &
locust -f carga/locustfile.py --headless --host http://127.0.0.1:8000 \
  -u 2000 -r 50 -t 5m --processes 2 --csv resultado/carga --only-summary
USUARIOS=2000 python -m carga.avaliar resultado/carga_stats.csv
```
