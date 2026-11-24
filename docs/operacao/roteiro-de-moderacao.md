# Roteiro de moderação

Este roteiro diz, passo a passo, como a equipe modera o Bandejão. Não existe tela administrativa (RNF08, [ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md)): a moderação é feita por consultas diretas ao banco, e por isso cada operação tem **checagem antes**, **mudança dentro de uma transação** e **verificação depois**.

> Quem pode usar: só os membros da equipe com usuário próprio no MySQL (veja [Quem tem acesso](#quem-tem-acesso)). Ações de moderação mexem em dados pessoais (RNF07): faça só o que o caso pede e não copie dados de contas para fora da VM.

## Antes de começar

1. Entre na VM e abra o MySQL com o **seu** usuário (nunca o `root` para moderar):

```bash
ssh -i <sua-chave> azureuser@20.102.232.122
cd ~/2026-2-Bandejao-UnB
docker compose exec db mysql -u <seu-usuário> -p bandejao
```

2. O papel `equipe_moderacao` permite `SELECT`, `INSERT`, `UPDATE` e `DELETE` no banco, sem mudar a estrutura das tabelas ([deploy de produção](deploy/deploy-producao.md?id=infraestrutura)).
3. Padrão de toda mudança:

```sql
START TRANSACTION;
-- 1. conferir o alvo (SELECT)
-- 2. UPDATE com WHERE pela chave (id), nunca sem WHERE
-- 3. conferir o resultado (SELECT) e o número de linhas afetadas
COMMIT;      -- se tudo certo
-- ROLLBACK; -- se algo saiu diferente do esperado
```

Regras: o `UPDATE` sempre filtra pela chave primária (`id`) e deve afetar **1 linha**; se afetar outro número, faça `ROLLBACK`. Registre cada ação no grupo da equipe (quem, qual conta ou avaliação pelo `id`, motivo), sem escrever a matrícula.

> O SQL direto **não atualiza** `atualizado_em` sozinho (o `auto_now` é do Django). Onde isso importa, o roteiro mostra o campo no `UPDATE`.

## 1. Ocultar uma avaliação

Quando: comentário ofensivo ou abusivo. A avaliação continua no banco, mas some das listas e das médias, e uma avaliação oculta deixa de pontuar.

```sql
START TRANSACTION;

SELECT id, usuario_id, refeicao_id, nota, comentario, oculta
FROM avaliacao_avaliacao WHERE id = <id>;

UPDATE avaliacao_avaliacao SET oculta = 1 WHERE id = <id>;
-- esperado: 1 row affected

SELECT id, oculta FROM avaliacao_avaliacao WHERE id = <id>;
COMMIT;
```

Para desfazer: o mesmo `UPDATE` com `oculta = 0`. Os pontos já concedidos pela avaliação **não** voltam sozinhos; se a equipe decidir retirá-los, use a [operação 4](#4-corrigir-pontos).

## 2. Suspender e reativar uma conta

Conta suspensa não entra: o login é recusado e as sessões abertas caem na próxima requisição ([ADR 0007](arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md)). Os dados e as avaliações ficam.

```sql
START TRANSACTION;

SELECT id, apelido, status, email_confirmado
FROM cadastro_usuario WHERE id = <id>;

UPDATE cadastro_usuario SET status = 'suspenso' WHERE id = <id> AND status = 'ativo';
-- esperado: 1 row affected (0 = a conta não estava ativa: ROLLBACK e investigue)

SELECT id, status FROM cadastro_usuario WHERE id = <id>;
COMMIT;
```

Para reativar: `SET status = 'ativo' WHERE id = <id> AND status = 'suspenso'`. Nunca troque `pendente` por `ativo` à mão: pendente significa e-mail não confirmado.

## 3. Excluir uma conta

Quando: solicitação do titular (RNF07, LGPD) ou decisão da moderação. **Nunca** apague a conta com `DELETE` direto: o apagamento em cascata dos contadores e o `SET NULL` das avaliações são feitos pelo código (BD-12). Use o comando:

```bash
cd ~/2026-2-Bandejao-UnB
docker compose exec backend python manage.py remover_conta <conta_id>
```

Na mesma transação, o comando apaga os contadores de gamificação (a conta sai do ranking), tira a conta e a hora exata dos registros de fila, encerra as sessões e apaga a conta com os tokens. As avaliações ficam e passam a aparecer como "usuário removido". A matrícula, o e-mail e o apelido ficam livres para um novo cadastro. Se a conta já não existe, ele avisa que ignorou e não falha. Confira depois:

```sql
SELECT COUNT(*) FROM cadastro_usuario WHERE id = <conta_id>;           -- esperado: 0
SELECT COUNT(*) FROM gamificacao_pontuacaousuario WHERE usuario_id = <conta_id>;  -- esperado: 0
```

A exclusão **não tem desfazer**; o único caminho de volta é restaurar um backup, que guarda a conta por até 7 dias (BD-15, [ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md)). Confira o `id` duas vezes antes de rodar.

## 4. Corrigir pontos

Quando: erro de pontuação (limitação L14: erros só se corrigem por ajuste manual) ou retirada de pontos de uma avaliação oculta. Há **duas** tabelas e as duas devem ficar coerentes: o total da conta e os pontos do semestre no campus.

```sql
START TRANSACTION;

SELECT usuario_id, pontos_totais, sequencia_atual, atualizado_em
FROM gamificacao_pontuacaousuario WHERE usuario_id = <id>;
SELECT id, campus_id, semestre_referencia, pontos, atualizado_em
FROM gamificacao_pontossemestrecampus WHERE usuario_id = <id>;

UPDATE gamificacao_pontuacaousuario
SET pontos_totais = pontos_totais - <n>
WHERE usuario_id = <id>;
-- esperado: 1 row affected

UPDATE gamificacao_pontossemestrecampus
SET pontos = pontos - <n>
WHERE id = <id_da_linha>;
-- NÃO mexa em atualizado_em aqui (veja abaixo)

SELECT pontos_totais FROM gamificacao_pontuacaousuario WHERE usuario_id = <id>;
SELECT pontos FROM gamificacao_pontossemestrecampus WHERE id = <id_da_linha>;
COMMIT;
```

Cuidados:

- Os pontos não podem ficar negativos (restrição `CHECK >= 0` nas duas tabelas): se o `UPDATE` falhar por isso, é `ROLLBACK` e o valor é menor do que o previsto.
- `atualizado_em` de `gamificacao_pontossemestrecampus` é o **desempate do ranking**. Corrigir pontos não deve mexer nele; só quem pontua muda esse campo.
- Se a conta não tem linha em `gamificacao_pontuacaousuario`, nada a corrigir.

## 5. Matrícula contestada

Quando: alguém diz que uma conta foi criada com a matrícula ou o SIAPE dele (L01). O sistema não valida a matrícula contra a universidade, então a resolução é manual. A matrícula é guardada em texto claro ([ADR 0008](arquitetura/adr/0008-matricula-siape-em-texto-claro.md)) e se recupera a partir do apelido.

```sql
SELECT id, apelido, matricula_siape, status, email_institucional, criado_em
FROM cadastro_usuario WHERE apelido = '<apelido>';
```

Passos:

1. Peça ao contestante uma prova de que a matrícula é dele (o canal de contato do site) e compare com o e-mail institucional da conta.
2. Se a contestação procede: [suspenda a conta](#2-suspender-e-reativar-uma-conta) e, depois, [exclua](#3-excluir-uma-conta) se for o caso. Isso libera a matrícula para o titular real se cadastrar (`matricula_siape` é única).
3. Se não procede: registre no grupo e responda ao contestante.

Não envie a matrícula de uma conta a terceiros.

## Testar o roteiro sem mudar nada

Para ensaiar uma operação em produção, termine sempre com `ROLLBACK` em vez de `COMMIT` e confira o `SELECT` antes de sair. A exclusão de conta (operação 3) não tem `ROLLBACK`: ensaie só em ambiente de teste.

## Quem tem acesso

| Pessoa | Usuário MySQL | Papel |
|---|---|---|
| _(preencher com os nomes da equipe)_ | _(usuário individual)_ | `equipe_moderacao` |

O acesso é conferido na VM (`~/.ssh/authorized_keys`) e no MySQL (`SELECT user, host FROM mysql.user;`). Cada membro tem usuário próprio; o `root` é só para administração. Quando alguém sair da equipe, remova a chave e o usuário no mesmo dia.
