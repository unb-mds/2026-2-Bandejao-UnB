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

**Resultado:** a previsão usa o índice com a consulta mais simples. O
ranking, no MySQL, só usa o índice se a elegibilidade (adesão e conta ativa)
ficar num `EXISTS` dentro de um `CASE`; com join, o MySQL lê todas as contas
e ordena em arquivo temporário (ver "O caso do ranking no MySQL").

## Como a conferência é feita

`tests/test_indices_bd10.py` roda nos jobs `testes` (SQLite) e
`testes-mysql` (MySQL 8.4) do CI:

1. Cria 5 campi, 120 contas (metade aderiu ao ranking, 1 em cada 10
   suspensa), 3.600 check-ins (12 semanas de segunda a sexta, 3 refeições,
   4 faixas, parte sem vínculo com a conta, como depois da retenção) e
   1.200 linhas de pontos (2 semestres).
2. Atualiza as estatísticas (`ANALYZE TABLE` no MySQL, `ANALYZE` no SQLite).
3. Roda `EXPLAIN` nas três consultas e confere o índice escolhido. No
   ranking, confere também que a ordem sai do índice (sem `Using filesort`
   nem `Using temporary` no MySQL, sem `TEMP B-TREE FOR ORDER BY` no SQLite).
4. Executa as consultas e confere o resultado, para garantir que o plano é de
   uma consulta que devolve o que a previsão e o ranking precisam. No
   ranking, o teste fixa um `atualizado_em` embaralhado em cada linha (fora
   da ordem de criação), cria um empate no topo e compara a consulta com o
   top 10 calculado em Python a partir dos dados: mesmas linhas, na mesma
   ordem. Assim um desempate errado (por id, por exemplo) ou uma
   elegibilidade que descarte contas que deveriam entrar faz o teste falhar.

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
elegivel = Exists(
    PontuacaoUsuario.objects.filter(
        usuario_id=OuterRef("usuario_id"),
        participa_ranking=True,
        usuario__status=StatusUsuario.ATIVO,
    )
)
(
    PontosSemestreCampus.objects.filter(
        campus=campus, semestre_referencia=semestre, pontos__gte=1
    )
    .alias(elegivel=Case(When(elegivel, then=Value(True)), default=Value(False)))
    .filter(elegivel=True)
    .order_by("-pontos", "atualizado_em")[:10]
)
```

O apelido e a patente das 10 linhas vêm numa segunda consulta, pelos ids
(por exemplo, `Usuario.objects.in_bulk(ids)`), e não por `select_related`.

### O caso do ranking no MySQL

No MySQL 8.4, todas as formas abaixo fazem o otimizador começar pela tabela
de contas (`cadastro_usuario` ou `gamificacao_pontuacaousuario`), ler todas
as linhas, buscar os pontos pelo UNIQUE e ordenar com `Using temporary;
Using filesort`:

| Forma | Índice do ranking | Ordenação em arquivo |
|---|---|---|
| Join (`usuario__status=…`, `usuario__pontuacao__participa_ranking=True`) | não | sim |
| `EXISTS` ou `usuario__in=Subquery` soltos no `filter` | não (o MySQL os transforma em join) | sim |
| Join com histogramas em `status` e `participa_ranking` | não | sim |
| `EXISTS` dentro de `CASE`, mas com `select_related("usuario")` | não | sim |
| Join com a dica `/*+ JOIN_PREFIX(...) */` (SQL cru) | sim | não |
| **`EXISTS` dentro de `CASE`, sem `select_related`** | **sim** | **não** |

O motivo: sem estatística dos valores, o MySQL supõe que só 10% das contas
estão ativas e aderiram ao ranking, e acha mais barato começar pela tabela de
contas do que percorrer o índice. O `CASE` impede que a subconsulta vire
join; assim a consulta tem uma tabela só no `FROM`, o MySQL lê o índice já
em ordem e para quando acha as 10 linhas elegíveis, conferindo cada uma pela
chave primária. A dica `JOIN_PREFIX` também resolve, mas exige SQL cru no
repositório. As variantes foram comparadas no CI do PR #160 (execuções
44465000702 e 44465684462).

### Regras para quem implementar a BE-15 e a BE-17

- Filtre por **igualdade** em `campus` e `tipo_refeicao` e use `data__in` (ou
  igualdade) em `data`. Um filtro por intervalo de datas (`data__range`)
  também usa o índice, mas lê os dias da semana que não entram na janela.
- No ranking, use a forma acima: elegibilidade em `EXISTS` dentro de `CASE`,
  com `alias` (e não `annotate`, que repetiria a subconsulta no `SELECT`), e
  sem join nem `select_related`. Filtre por igualdade em `campus` e
  `semestre_referencia` e ordene exatamente por `-pontos, atualizado_em`. Outra ordem (por exemplo,
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
  CORRELATED SCALAR SUBQUERY 1
    SEARCH U0 USING INDEX sqlite_autoindex_gamificacao_pontuacaousuario_1 (usuario_id=?)
    SEARCH U1 USING INTEGER PRIMARY KEY (rowid=?)
```

O `TEMP B-TREE FOR GROUP BY` da contagem é esperado: o agrupamento é por
`data` e `faixa_inicio`, e `faixa_inicio` não está no índice. O
agrupamento é feito só sobre as linhas que o índice já selecionou (4 dias de
uma refeição de um campus), então não vale a pena um índice só para isso.

## Plano no MySQL 8.4 (CI)

Execução 44466578120 do PR #160 (commit `410de07`), job `testes-mysql`.
Colunas principais do `EXPLAIN`:

```text
contarPorFaixa
  fila_checkin  type=range  key=checkin_campus_tipo_data_idx  rows=16
    possible_keys=checkin_campus_tipo_data_idx,fila_checkin_data_1a0e93d4
    Extra: Using index condition; Using temporary

temposDeEspera
  fila_checkin  type=range  key=checkin_campus_tipo_data_idx  rows=16
    possible_keys=checkin_campus_tipo_data_idx,fila_checkin_data_1a0e93d4
    Extra: Using index condition; Using where

ranking
  gamificacao_pontossemestrecampus  PRIMARY  type=range  key=pontos_semestre_ranking_idx  rows=118
    Extra: Using index condition; Using where
  U0 (gamificacao_pontuacaousuario)  DEPENDENT SUBQUERY  type=eq_ref  key=usuario_id
  U1 (cadastro_usuario)              DEPENDENT SUBQUERY  type=eq_ref  key=PRIMARY
```

O `Using temporary` da contagem é o mesmo caso do `TEMP B-TREE` do SQLite: o
agrupamento por `faixa_inicio`, sobre as 16 linhas que o índice selecionou. O
ranking não tem `Using filesort` nem `Using temporary`: a ordem sai do índice.
