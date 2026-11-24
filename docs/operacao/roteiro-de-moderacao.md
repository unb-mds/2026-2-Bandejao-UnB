# Roteiro de moderação

Este roteiro diz, passo a passo, como a equipe modera o Bandejão. Não existe tela administrativa (RNF08, [ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md)): a moderação é feita por consultas diretas ao banco, e por isso cada operação tem **checagem antes**, **mudança dentro de uma transação** e **verificação depois**.

> Quem pode usar: só os membros da equipe com usuário próprio no MySQL (veja [Quem tem acesso](#quem-tem-acesso)). Ações de moderação mexem em dados pessoais (RNF07): faça só o que o caso pede e não copie dados de contas para fora da VM.

## Antes de começar

1. Entre na VM e abra o MySQL com o **seu** usuário (nunca o `root` para moderar):

```bash
ssh -i <sua-chave> azureuser@<IP da VM>   # o IP está em deploy/deploy-producao.md (Infraestrutura)
cd ~/2026-2-Bandejao-UnB
docker compose exec db mysql -u <seu-usuário> -p bandejao
```

2. O papel `equipe_moderacao` permite `SELECT`, `INSERT`, `UPDATE` e `DELETE` no banco, sem mudar a estrutura das tabelas ([permissões no deploy de produção](deploy/deploy-producao.md?id=banco); criação de usuário em [Acesso da equipe](deploy/deploy-producao.md?id=acesso-da-equipe)).
3. Padrão de toda mudança:

```sql
START TRANSACTION;
-- 1. conferir o alvo (SELECT)
-- 2. UPDATE com WHERE pela chave (id), nunca sem WHERE
-- 3. conferir o resultado (SELECT) e o número de linhas afetadas
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Regras:

- **O `COMMIT` nunca vem escrito nos blocos.** Ao colar um bloco no cliente `mysql`, um erro numa linha não interrompe as seguintes; um `COMMIT` colado junto gravaria uma mudança pela metade. Por isso o bloco para antes: confira o resultado e só então digite `COMMIT;` (ou `ROLLBACK;`).
- O `UPDATE` sempre filtra pela chave (o `id` da linha) e deve afetar **1 linha**; se afetar outro número, ou se qualquer comando do bloco der erro, digite `ROLLBACK;`.
- Não leve ids, matrículas ou e-mails para fora da VM (por exemplo, para um chat). A equipe decidiu não manter registro manual das ações de moderação ([ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md), Consequências).

> O SQL direto **não muda** `atualizado_em` (o `auto_now` é do Django), e isso é desejado: veja a [operação 4](#4-corrigir-pontos).

## 1. Ocultar uma avaliação

Quando: comentário ofensivo ou abusivo. A avaliação continua no banco, mas some das listas e das médias, e uma avaliação oculta deixa de pontuar.

```sql
START TRANSACTION;

SELECT id, usuario_id, refeicao_id, nota, comentario, oculta
FROM avaliacao_avaliacao WHERE id = <id>;

UPDATE avaliacao_avaliacao SET oculta = 1 WHERE id = <id>;
-- esperado: 1 row affected

SELECT id, oculta FROM avaliacao_avaliacao WHERE id = <id>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Para desfazer: o mesmo `UPDATE` com `oculta = 0`. Os pontos já concedidos pela avaliação **não** voltam sozinhos; se a equipe decidir retirá-los, use a [operação 4](#4-corrigir-pontos). Se os pontos já tinham sido retirados pela operação 4 e a avaliação voltar a ser exibida, devolva-os também, com a mesma operação 4 e `+ <n>` no lugar de `- <n>`, nas duas tabelas.

## 2. Suspender e reativar uma conta

Conta suspensa não entra: o login é recusado e as sessões abertas caem na próxima requisição ([ADR 0007](arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md)). Os dados e as avaliações ficam.

```sql
START TRANSACTION;

SELECT id, apelido, status, email_confirmado
FROM cadastro_usuario WHERE id = <id>;

UPDATE cadastro_usuario SET status = 'suspenso' WHERE id = <id> AND status = 'ativo';
-- esperado: 1 row affected (0 = a conta não estava ativa: ROLLBACK e investigue)

SELECT id, status FROM cadastro_usuario WHERE id = <id>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Para reativar: `SET status = 'ativo' WHERE id = <id> AND status = 'suspenso'`. Nunca troque `pendente` por `ativo` à mão: pendente significa e-mail não confirmado.

## 3. Excluir uma conta

Quando: solicitação do titular (RNF07, LGPD) ou decisão da moderação. **Nunca** apague a conta com `DELETE` direto: o apagamento em cascata dos contadores e o `SET NULL` das avaliações são feitos pelo código (BD-12). Use o comando, que roda com o usuário da aplicação, dentro do container `backend` (não com o seu usuário MySQL).

**A exclusão não tem desfazer.** Antes de rodar, tire um backup à mão e confira o `id` duas vezes:

```bash
cd ~/2026-2-Bandejao-UnB
mkdir -p ~/backups
(umask 077 && docker compose exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot bandejao --single-transaction --routines --events --triggers' |
    gzip > ~/backups/antes-remover-conta-$(date -u +%Y%m%dT%H%M%SZ).sql.gz)
ls -l ~/backups/antes-remover-conta-*.sql.gz | tail -1     # o tamanho não pode ser 0
zcat "$(ls -1 ~/backups/antes-remover-conta-*.sql.gz | tail -1)" | tail -1   # esperado: "-- Dump completed ..."
```

**Se o titular pediu que as avaliações dele também sejam apagadas** ([ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md), revisão de 14/11), apague-as **antes** do comando, porque depois dele o `usuario_id` das avaliações vira `NULL` e não dá mais para achá-las:

```sql
START TRANSACTION;
SELECT COUNT(*) FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;
DELETE FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;
SELECT COUNT(*) FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;  -- esperado: 0
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Sem esse pedido, pule o bloco acima: as avaliações ficam e passam a aparecer como "usuário removido". Depois, a exclusão da conta:

```bash
docker compose exec backend python manage.py remover_conta <conta_id>
```

Na mesma transação, o comando apaga os contadores de gamificação (a conta sai do ranking), tira a conta e a hora exata dos registros de fila, encerra as sessões e apaga a conta com os tokens. A matrícula, o e-mail e o apelido ficam livres para um novo cadastro. Se a conta não existe, o comando termina com erro (`A conta <id> não existe.`) e nada muda; se já foi excluída, termina com erro (`... já foi excluída.`). Confira depois:

```sql
SELECT COUNT(*) FROM cadastro_usuario WHERE id = <conta_id>;           -- esperado: 0
SELECT COUNT(*) FROM gamificacao_pontuacaousuario WHERE usuario_id = <conta_id>;  -- esperado: 0
```

O único caminho de volta é restaurar um backup. Hoje existem os backups feitos a cada deploy (`~/backups/deploy-*.sql.gz`, os 10 mais recentes, mais o `ultimo-ok.sql.gz`) e o que você tirou acima; só serve para uma conta que já existia na data do backup. O backup diário de 7 dias (BD-15) passa a valer quando estiver instalado na VM ([backup do banco](deploy/backup-banco.md)); até lá, não conte com ele.

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
WHERE id = <id_da_linha> AND usuario_id = <id>;
-- esperado: 1 row affected (0 = o id da linha não é desta conta: ROLLBACK)
-- NÃO mexa em atualizado_em aqui (veja abaixo)

SELECT pontos_totais FROM gamificacao_pontuacaousuario WHERE usuario_id = <id>;
SELECT pontos FROM gamificacao_pontossemestrecampus WHERE id = <id_da_linha>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Cuidados:

- A linha certa de `gamificacao_pontossemestrecampus` é a do campus e do semestre em que o ponto foi dado. Confira no primeiro `SELECT` e use o `id` dela, junto com o `usuario_id` da conta.
- Os pontos não podem ficar negativos (restrição `CHECK >= 0` nas duas tabelas). Se o primeiro `UPDATE` passar e o segundo falhar por isso, o total já foi mudado e a outra tabela não: digite `ROLLBACK;`. Por isso o `COMMIT` fica de fora.
- Tirar pontos de `pontos_totais` pode baixar a patente da conta.
- `atualizado_em` de `gamificacao_pontossemestrecampus` é o **desempate do ranking**. Corrigir pontos não deve mexer nele; só quem pontua muda esse campo.
- Se a conta não tem linha em `gamificacao_pontuacaousuario`, nada a corrigir. Para devolver pontos, use o mesmo bloco com `+ <n>`.

## 5. Matrícula contestada

Quando: alguém diz que uma conta foi criada com a matrícula ou o SIAPE dele (L01). O sistema não valida a matrícula contra a universidade, então a resolução é manual. A matrícula é guardada em texto claro ([ADR 0008](arquitetura/adr/0008-matricula-siape-em-texto-claro.md)) e se recupera a partir do apelido.

```sql
SELECT id, apelido, matricula_siape, status, email_institucional, criado_em
FROM cadastro_usuario WHERE apelido_normalizado = '<apelido>';
```

O `apelido` não é único; o que é único é o `apelido_normalizado`, que é o apelido sem acentos e em minúsculas. Escreva o apelido assim na busca e ela devolve no máximo 1 linha, qualquer que seja a collation.

Passos:

1. Peça ao contestante uma prova de que a matrícula é dele (o canal de contato do site) e compare com o e-mail institucional da conta.
2. Se a contestação procede: [suspenda a conta](#2-suspender-e-reativar-uma-conta) e, depois, [exclua](#3-excluir-uma-conta) se for o caso. Isso libera a matrícula para o titular real se cadastrar (`matricula_siape` é única).
3. Se não procede: registre no grupo e responda ao contestante.

Não envie a matrícula de uma conta a terceiros.

## Testar o roteiro sem mudar nada

Para ensaiar uma operação em produção, digite `ROLLBACK;` em vez de `COMMIT;` e confira o `SELECT` antes de sair. A exclusão de conta (operação 3) não tem `ROLLBACK`: ensaie só em ambiente de teste. A operação 5 só tem `SELECT` e não precisa de `ROLLBACK`.

## Quem tem acesso

Há duas portas, e a lista abaixo cobre as duas:

| Pessoa | Usuário MySQL | Papel | Acesso SSH à VM | Última conferência |
|---|---|---|---|---|
| Álvaro | `alvaro` | `equipe_moderacao` | sim | 24/11/2026 |
| Luís | `luis` | `equipe_moderacao` | sim | 24/11/2026 |

- **SSH:** é um único usuário, `azureuser`, com uma chave por pessoa em `~/.ssh/authorized_keys`. Quem entra na VM e tem acesso ao Docker consegue ler a senha do `root` do MySQL ([Acesso da equipe](deploy/deploy-producao.md?id=acesso-da-equipe)). Por isso a chave SSH vale tanto quanto o usuário MySQL.
- **MySQL:** cada pessoa tem usuário próprio (`SELECT user, host FROM mysql.user;`). O `root` é só para administração.

Hoje há dois usuários individuais; quem precisar moderar pede ao grupo para criar o seu (veja o deploy de produção). Quando alguém sair da equipe, remova a chave e o usuário no mesmo dia e atualize a data da conferência. Sem isso, a lista envelhece em silêncio.
