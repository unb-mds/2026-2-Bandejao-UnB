# BD-10 — Índices da previsão e do ranking

> Issue: [#150](https://github.com/unb-mds/2026-2-Bandejao-UnB/issues/150) · Requisito: RNF01 · Teste: `backend/tests/test_indices_bd10.py`

O Nível 4 do banco define dois índices compostos para as consultas que mais
pesam no RNF01:

| Tabela | Índice (nome no banco) | Colunas | Consulta |
|---|---|---|---|
| `CHECKIN` | `checkin_campus_tipo_data_idx` | `campus_id`, `tipo_refeicao`, `data` | Previsão de pico (RF13) e espera estimada (RN08), Fila N4 4c |
| `PONTOS_SEMESTRE_CAMPUS` | `pontos_semestre_ranking_idx` | `campus_id`, `semestre_referencia`, `pontos` desc, `atualizado_em` | Ranking do semestre e desempate (RF27.2), Gamificação N4 4c |

Os dois já foram criados pela migration `0001_initial` de cada app (BD-01). A
BD-10 conferiu, com dados de teste e `EXPLAIN`, que o otimizador **escolhe**
esses índices, e não os de uma coluna que também serviriam (`data`,
`campus_id`, `usuario_id` e o UNIQUE de pontos).

## Como a conferência é feita

`tests/test_indices_bd10.py` roda nos jobs `testes` (SQLite) e
`testes-mysql` (MySQL 8.4) do CI:

1. Cria 5 campi, 120 contas (metade aderiu ao ranking, 1 em cada 10
   suspensa), 3.600 check-ins (12 semanas de segunda a sexta, 3 refeições,
   4 faixas, parte sem vínculo com a conta, como depois da retenção) e
   1.200 linhas de pontos (2 semestres).
2. Atualiza as estatísticas (`ANALYZE TABLE` no MySQL, `ANALYZE` no SQLite).
3. Roda `EXPLAIN` nas três consultas e confere o índice escolhido. No
   ranking, confere também que a ordem sai do índice (sem `Using filesort`).
4. Executa as consultas e confere o resultado, para garantir que o plano é de
   uma consulta que devolve o que a previsão e o ranking precisam.

**Prova do vermelho:** com uma migration local (descartada) que remove os dois
índices, os três testes de plano falham: a previsão passa a usar o índice de
`data` e o ranking, o UNIQUE (`usuario_id`, `campus_id`,
`semestre_referencia`).

O passo "EXPLAIN dos índices (BD-10)" do job `testes-mysql` repete só esses
testes com `-s`, para o plano do MySQL ficar no log do CI.

## Consultas conferidas

O `PrevisaoService` (BE-15) e o `RankingService` (BE-17) ainda não existem. As
consultas do teste têm a forma que o Nível 4 do backend descreve para os
métodos dos repositórios:

**`CheckinRepository.contarPorFaixa`** (previsão de pico):

```python
Checkin.objects.filter(campus=campus, tipo_refeicao=tipo, data__in=datas_da_janela)
    .values("data", "faixa_inicio")
    .annotate(quantidade=Count("id"))
    .order_by()
```

**`CheckinRepository.temposDeEspera`** (espera estimada):

```python
Checkin.objects.filter(
    campus=campus, tipo_refeicao=tipo, data__in=datas_da_janela,
    tempo_espera_min__isnull=False,
).values("data", "faixa_inicio", "tempo_espera_min")
```

**`PontuacaoRepository.elegiveis`** + tamanho do ranking:

```python
PontosSemestreCampus.objects.filter(
    campus=campus, semestre_referencia=semestre, pontos__gte=1,
    usuario__status=StatusUsuario.ATIVO,
    usuario__pontuacao__participa_ranking=True,
).select_related("usuario").order_by("-pontos", "atualizado_em")[:10]
```

### Regras para quem implementar a BE-15 e a BE-17

- Filtre por **igualdade** em `campus` e `tipo_refeicao` e use `data__in` (ou
  igualdade) em `data`. Um filtro por intervalo de datas (`data__range`)
  também usa o índice, mas lê os dias da semana que não entram na janela.
- No ranking, filtre por igualdade em `campus` e `semestre_referencia` e
  ordene exatamente por `-pontos, atualizado_em`. Outra ordem (por exemplo,
  `-atualizado_em` no desempate ou ordenar pelo apelido) faz o banco ordenar
  em arquivo temporário. O `LIMIT` (tamanho do ranking) fica no banco, não em
  Python.
- Não troque o `Count("id")` por agregação em Python: o índice só ajuda se o
  banco fizer o agrupamento.
- Se a consulta mudar, rode `tests/test_indices_bd10.py` trocando a função
  `consulta_*` correspondente pela chamada ao repositório.

## Plano no SQLite (local, 19/11/2026)

```text
contarPorFaixa
  SEARCH fila_checkin USING INDEX checkin_campus_tipo_data_idx (campus_id=? AND tipo_refeicao=? AND data=?)
  USE TEMP B-TREE FOR GROUP BY

temposDeEspera
  SEARCH fila_checkin USING INDEX checkin_campus_tipo_data_idx (campus_id=? AND tipo_refeicao=? AND data=?)

ranking
  SEARCH gamificacao_pontossemestrecampus USING INDEX pontos_semestre_ranking_idx (campus_id=? AND semestre_referencia=? AND pontos>?)
  SEARCH cadastro_usuario USING INTEGER PRIMARY KEY (rowid=?)
  SEARCH gamificacao_pontuacaousuario USING INDEX sqlite_autoindex_gamificacao_pontuacaousuario_1 (usuario_id=?)
```

O `TEMP B-TREE FOR GROUP BY` da contagem é esperado: o agrupamento é por
`data` e `faixa_inicio`, e `faixa_inicio` não está no índice. O
agrupamento é feito só sobre as linhas que o índice já selecionou (4 dias de
uma refeição de um campus), então não vale a pena um índice só para isso.

## Plano no MySQL 8.4 (CI)

PENDENTE_MYSQL
