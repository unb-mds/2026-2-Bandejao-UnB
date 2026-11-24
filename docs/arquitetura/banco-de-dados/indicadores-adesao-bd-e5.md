# BD-E5 — Consultas dos indicadores de adesão (RNF09)

> Requisito: RNF09 · Teste: `backend/tests/test_indicadores_adesao_bd_e5.py`

A RNF09 pede que a equipe calcule, **por consulta manual ao banco** (sem
ferramenta de análise e sem tela administrativa), quatro indicadores
descritivos de adesão. Este documento traz as quatro consultas. O teste lê os
blocos `sql` **deste arquivo** e os executa nos dois bancos do CI (SQLite e
MySQL 8.4) sobre dados com resposta conhecida; por isso o texto abaixo não
pode divergir do que foi testado.

## Como rodar em produção

Na VM, abrir o cliente MySQL no container do banco (a senha vem do ambiente
do container, não é digitada na linha de comando):

```bash
docker compose exec db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot "$MYSQL_DATABASE"'
```

Primeiro, a variável com o início da janela (4 semanas, a mesma da retenção,
RNF07.3 e RNF09):

```sql
SET @inicio = CURDATE() - INTERVAL 28 DAY;
```

Depois, colar uma consulta por vez. As quatro só **leem** o banco (`SELECT`).
Não gravam nem mostram matrícula, e-mail ou apelido: o resultado são
contagens e uma porcentagem.

## Definições usadas

| Termo | Definição |
|---|---|
| Janela | Check-ins com `data` de `@inicio` em diante: as 4 semanas que a retenção mantém. |
| Usuário ativo (indicador 2) | Conta com ao menos um check-in na janela (RNF09). |
| Base dos indicadores 3 e 4 | Contas com `status = 'ativo'` (contas pendentes e suspensas não entram). |
| Resultado sem dado | Se o denominador for zero, a porcentagem sai `NULL` em vez de dar erro. |

A RNF09 não diz qual é a base das porcentagens 3 e 4. A escolha acima (todas
as contas ativas, e não só as que fizeram check-in) mede a adesão no conjunto
de quem poderia aderir. Se a equipe preferir medir só entre quem fez
check-in, basta trocar a base; as contagens que a consulta já devolve
(`contas_ativas`, `com_sequencia`, `no_ranking`) permitem refazer a conta.

## 1. Pergunta de saída respondida

Porcentagem de check-ins da janela cuja pergunta de saída foi respondida
(`PERGUNTA_SAIDA.estado = 'respondida'`). Conta também os check-ins que já
perderam o vínculo com a conta, porque o dado não é pessoal.

```sql
SELECT COUNT(*) AS checkins,
       SUM(CASE WHEN p.estado = 'respondida' THEN 1 ELSE 0 END) AS respondidas,
       ROUND(100.0 * SUM(CASE WHEN p.estado = 'respondida' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 1) AS pct_respondidas
FROM fila_checkin c
LEFT JOIN fila_perguntasaida p ON p.checkin_id = c.id
WHERE c.data >= @inicio;
```

## 2. Check-ins por usuário ativo por semana

Média de check-ins por conta que fez ao menos um check-in na janela, por
semana (janela de 4 semanas). Só conta check-ins ainda ligados a uma conta.

```sql
SELECT COUNT(*) AS checkins,
       COUNT(DISTINCT c.usuario_id) AS usuarios_ativos,
       ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT c.usuario_id) * 4, 0), 2)
           AS checkins_por_usuario_por_semana
FROM fila_checkin c
WHERE c.data >= @inicio
  AND c.usuario_id IS NOT NULL;
```

## 3. Sequência de 2 semanas ou mais

Porcentagem das contas ativas com `sequencia_atual` de 2 ou mais.

```sql
SELECT COUNT(*) AS contas_ativas,
       SUM(CASE WHEN COALESCE(g.sequencia_atual, 0) >= 2 THEN 1 ELSE 0 END)
           AS com_sequencia,
       ROUND(100.0 * SUM(CASE WHEN COALESCE(g.sequencia_atual, 0) >= 2
                              THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 1) AS pct_com_sequencia
FROM cadastro_usuario u
LEFT JOIN gamificacao_pontuacaousuario g ON g.usuario_id = u.id
WHERE u.status = 'ativo';
```

> **Atenção:** a coluna `sequencia_atual` só é atualizada quando a BE-E6
> (`SequenciaService`) estiver no ar. Até lá o indicador sai 0% mesmo com
> contas engajadas, e isso não é erro da consulta. O backend avalia a quebra
> da sequência **na leitura**, e a coluna guarda o último valor gravado: o
> número aqui pode ficar um pouco acima do que cada pessoa vê no app.

## 4. Adesão ao ranking

Porcentagem das contas ativas com `participa_ranking` ligado.

```sql
SELECT COUNT(*) AS contas_ativas,
       SUM(CASE WHEN g.participa_ranking = 1 THEN 1 ELSE 0 END) AS no_ranking,
       ROUND(100.0 * SUM(CASE WHEN g.participa_ranking = 1 THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 1) AS pct_no_ranking
FROM cadastro_usuario u
LEFT JOIN gamificacao_pontuacaousuario g ON g.usuario_id = u.id
WHERE u.status = 'ativo';
```

## Limites

- Os indicadores são descritivos: não há meta numérica nem comparação com
  período anterior, porque o check-in só existe a partir da Release 2
  (RNF09).
- A janela de 4 semanas é a mesma da retenção. Depois dela os check-ins
  perdem a conta, então o indicador 2 não pode olhar mais longe.
- Registro da execução em produção: rodar uma vez, anotar data e resultado
  no PR ou no documento da apresentação. O backlog pede que as consultas
  "rodem em produção".
