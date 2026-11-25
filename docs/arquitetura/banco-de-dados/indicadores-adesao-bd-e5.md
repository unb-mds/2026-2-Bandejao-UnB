# BD-E5 — Consultas dos indicadores de adesão (RNF09)

> Requisito: RNF09 · Teste: `backend/tests/test_indicadores_adesao_bd_e5.py`

A RNF09 pede que a equipe calcule, **por consulta manual ao banco** (sem
ferramenta de análise e sem tela administrativa), quatro indicadores
descritivos de adesão. Este documento traz as quatro consultas. O teste lê os
blocos `sql` **deste arquivo** e os executa nos dois bancos do CI (SQLite e
MySQL 8.4) sobre dados com resposta conhecida; por isso o texto abaixo não
pode divergir do que foi testado.

## Como rodar em produção

Na VM, entrar no cliente MySQL com o **próprio usuário** de banco, como
descreve o guia de deploy (`docs/deploy/deploy-producao.md`, "Acesso da
equipe"). O `-p` pede a senha sem mostrá-la, e o root não é usado:

```bash
docker compose exec db mysql -u <usuário> -p bandejao
```

Primeiro, a variável com o início da janela: as 4 semanas mais recentes, a
mesma quantidade que a retenção mantém (RNF07.3 e RNF09). São 28 datas, de
hoje até 27 dias atrás, contadas pelo **dia de Brasília** (UTC-3, sem horário
de verão desde 2019). O `CURDATE()` não serve aqui, porque segue o fuso do
servidor MySQL, que por padrão é UTC, e viraria o dia às 21h de Brasília.

```sql
SET @inicio = DATE(UTC_TIMESTAMP() - INTERVAL 3 HOUR) - INTERVAL 27 DAY;
```

Depois, colar uma consulta por vez, **na mesma sessão** (a variável vale só
nela). As quatro só **leem** o banco (`SELECT`). Não gravam nem mostram
matrícula, e-mail ou apelido: o resultado são contagens e uma porcentagem.

## Definições usadas

| Termo | Definição |
|---|---|
| Janela | Check-ins com `data` de `@inicio` em diante: as 28 datas mais recentes (4 semanas). A retenção guarda mais um dia (o dia-limite), que o indicador não usa. |
| Usuário ativo (indicador 2) | Conta com ao menos um check-in na janela (RNF09). Não filtra por `status`: conta suspensa com check-in na janela entra. |
| Base dos indicadores 3 e 4 | Contas com `status = 'ativo'` (contas pendentes e suspensas não entram). |
| Resultado sem dado | Sem linhas, as contagens saem 0 e a porcentagem (ou a média) sai `NULL` em vez de dar erro. |

A RNF09 não diz qual é a base das porcentagens 3 e 4. A escolha acima (todas
as contas ativas, e não só as que fizeram check-in) mede a adesão no conjunto
de quem poderia aderir. Se a equipe preferir medir só entre quem fez
check-in, **o numerador também muda**, então não basta refazer a conta com as
contagens devolvidas. Acrescente este trecho ao `WHERE` das consultas 3 e 4
(antes do `;`):

```sql
AND EXISTS (SELECT 1 FROM fila_checkin c
            WHERE c.usuario_id = u.id AND c.data >= @inicio)
```

O teste também roda essa variante.

## 1. Pergunta de saída respondida

Porcentagem de check-ins da janela cuja pergunta de saída foi respondida
(`PERGUNTA_SAIDA.estado = 'respondida'`). Conta também os check-ins que já
perderam o vínculo com a conta: dentro da janela, eles vêm de contas
excluídas (BD-12), e o dado não é pessoal.

```sql
SELECT COUNT(*) AS checkins,
       COALESCE(SUM(CASE WHEN p.estado = 'respondida' THEN 1 ELSE 0 END), 0)
           AS respondidas,
       ROUND(100.0 * SUM(CASE WHEN p.estado = 'respondida' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 1) AS pct_respondidas
FROM fila_checkin c
LEFT JOIN fila_perguntasaida p ON p.checkin_id = c.id
WHERE c.data >= @inicio;
```

> **Atenção:** a `PERGUNTA_SAIDA` só passa a ser gravada com a BE-E1. Até lá o
> indicador sai 0% quando há check-ins, e isso não é erro da consulta. Nas 4
> semanas seguintes, os check-ins anteriores à BE-E1 (sem pergunta) ainda
> entram no denominador.

## 2. Check-ins por usuário ativo por semana

**Média** (não porcentagem) de check-ins por conta que fez ao menos um
check-in na janela, por semana (4 semanas). Só conta check-ins ainda ligados a
uma conta.

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
       COALESCE(SUM(CASE WHEN COALESCE(g.sequencia_atual, 0) >= 2 THEN 1 ELSE 0 END), 0)
           AS com_sequencia,
       ROUND(100.0 * SUM(CASE WHEN COALESCE(g.sequencia_atual, 0) >= 2
                              THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 1) AS pct_com_sequencia
FROM cadastro_usuario u
LEFT JOIN gamificacao_pontuacaousuario g ON g.usuario_id = u.id
WHERE u.status = 'ativo';
```

> **Atenção:** a coluna `sequencia_atual` só passa a ser gravada com a BE-E6
> (a sequência semanal ainda não existe em `develop`). Até lá o indicador sai
> 0% mesmo com contas engajadas, e isso não é erro da consulta. Pelo desenho
> previsto, nada zera a coluna depois: quem deixa de usar o app continua com o
> último valor gravado, e o indicador pode **superestimar** a adesão. Reavaliar
> esta consulta quando a BE-E6 entrar.

## 4. Adesão ao ranking

Porcentagem das contas ativas com `participa_ranking` ligado.

```sql
SELECT COUNT(*) AS contas_ativas,
       COALESCE(SUM(CASE WHEN g.participa_ranking = 1 THEN 1 ELSE 0 END), 0)
           AS no_ranking,
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
- A janela de 4 semanas é a mesma quantidade da retenção. Depois dela os
  check-ins perdem a conta, então o indicador 2 não pode olhar mais longe.
- Se algum SQL deste documento mudar, rodar de novo em produção e atualizar o
  registro abaixo.

## Execução em produção

O backlog pede que as consultas "rodem em produção". Aqui ficam a data, quem
rodou e o resultado de cada indicador (só números; nada pessoal).

**24/11/2026**, no MySQL de produção, por Luís (usuário próprio de banco), com o SQL deste documento na versão do PR #283 e `@inicio` em 28/10/2026 (`SELECT @inicio` conferido antes das consultas):

| Indicador | Resultado |
|---|---|
| 1. Pergunta de saída respondida | 0 check-ins na janela, 0 respondidas, porcentagem `NULL` |
| 2. Check-ins por usuário ativo por semana | 0 check-ins, 0 usuários ativos, média `NULL` |
| 3. Sequência de 2 semanas ou mais | 3 contas ativas, 0 com sequência, 0,0% |
| 4. Adesão ao ranking | 3 contas ativas, 1 no ranking, 33,3% |

Como ler: ainda não há check-ins em produção (a Release 2 acabou de ir ao ar), então os indicadores 1 e 2 saem sem dado, como a consulta prevê; o `NULL` não é erro. O indicador 3 também sairia 0% por causa da BE-E6 (ver o aviso da consulta 3). Só o indicador 4 já tem número. Rodar de novo quando houver check-ins.
