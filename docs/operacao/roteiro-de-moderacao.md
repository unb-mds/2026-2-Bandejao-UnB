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
ROLLBACK;                -- descarta qualquer transação que tenha ficado aberta
START TRANSACTION;
-- 1. conferir o alvo (SELECT)
-- 2. UPDATE com WHERE pela chave (id), nunca sem WHERE
-- 3. conferir o resultado (SELECT) e o número de linhas afetadas
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Regras:

- **O `COMMIT` nunca vem escrito nos blocos.** Ao colar um bloco no cliente `mysql`, um erro numa linha não interrompe as seguintes; um `COMMIT` colado junto gravaria uma mudança pela metade. Por isso o bloco para antes: confira o resultado e só então digite `COMMIT;` (ou `ROLLBACK;`).
- **Todo bloco começa com `ROLLBACK;`.** No MySQL, o `START TRANSACTION` faz `COMMIT` da transação que estiver aberta. Se você colar um bloco duas vezes, ou colar outro depois de um que ficou sem resposta, o `ROLLBACK;` do começo descarta o que estava pendente, em vez de gravá-lo pela metade.
- O `UPDATE` sempre filtra pela chave (o `id` da linha) e deve afetar **1 linha**; se afetar outro número, ou se qualquer comando do bloco der erro, digite `ROLLBACK;`.
- **Não deixe uma transação aberta e parada.** Ela segura travas nas linhas, e quem precisar delas (o site, por exemplo) fica esperando. Termine sempre com `COMMIT;` ou `ROLLBACK;` antes de sair do `mysql`. Sair sem `COMMIT;` desfaz a mudança, sem aviso.
- Não leve ids, matrículas ou e-mails para fora da VM (por exemplo, para um chat). A equipe decidiu não manter registro manual das ações de moderação ([ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md), Consequências).

> O SQL direto **não muda** `atualizado_em` (o `auto_now` é do Django), e isso é desejado: veja a [operação 4](#_4-corrigir-pontos).

## 1. Ocultar uma avaliação

Quando: comentário ofensivo ou abusivo. A avaliação continua no banco, mas some das listas e das médias.

```sql
ROLLBACK;
START TRANSACTION;

SELECT id, usuario_id, refeicao_id, nota, comentario, oculta
FROM avaliacao_avaliacao WHERE id = <id>;

UPDATE avaliacao_avaliacao SET oculta = 1 WHERE id = <id>;
-- esperado: 1 row affected

SELECT id, oculta FROM avaliacao_avaliacao WHERE id = <id>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Ocultar **não retira os pontos** que a avaliação já deu. Se a equipe decidir retirá-los, use a [operação 4](#_4-corrigir-pontos), depois de ocultar.

**Para desfazer** (voltar a exibir a avaliação):

```sql
ROLLBACK;
START TRANSACTION;
UPDATE avaliacao_avaliacao SET oculta = 0 WHERE id = <id> AND oculta = 1;
-- esperado: 1 row affected
SELECT id, oculta FROM avaliacao_avaliacao WHERE id = <id>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Se os pontos já tinham sido retirados pela operação 4, devolva-os também, com o mesmo bloco da operação 4 e `+ <n>` no lugar de `- <n>`, nas duas tabelas.

## 2. Suspender e reativar uma conta

Conta suspensa não entra: o login é recusado e as sessões abertas caem na próxima requisição ([ADR 0007](arquitetura/adr/0007-sessao-autenticada-por-cookie-httponly.md)). Os dados e as avaliações ficam. As sessões **não são apagadas**: se a conta for reativada em até 14 dias (a duração da sessão), as que estavam abertas podem voltar a valer. Para encerrá-las de vez, é preciso excluir a conta ([operação 3](#_3-excluir-uma-conta)).

```sql
ROLLBACK;
START TRANSACTION;

SELECT id, apelido, status, email_confirmado
FROM cadastro_usuario WHERE id = <id>;

UPDATE cadastro_usuario SET status = 'suspenso' WHERE id = <id> AND status = 'ativo';
-- esperado: 1 row affected (0 = a conta não estava ativa: ROLLBACK e investigue)

SELECT id, status FROM cadastro_usuario WHERE id = <id>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

**Para reativar:**

```sql
ROLLBACK;
START TRANSACTION;
UPDATE cadastro_usuario SET status = 'ativo' WHERE id = <id> AND status = 'suspenso';
-- esperado: 1 row affected
SELECT id, status FROM cadastro_usuario WHERE id = <id>;
-- confira o resultado acima; se estiver certo, digite: COMMIT;   senão: ROLLBACK;
```

Nunca troque `pendente` por `ativo` à mão: pendente significa e-mail não confirmado. Uma conta `pendente` também não se suspende (o `UPDATE` acima afeta 0 linhas): se ela precisar sair, exclua-a pela [operação 3](#_3-excluir-uma-conta).

## 3. Excluir uma conta

Quando: solicitação do titular (RNF07, LGPD) ou decisão da moderação. **Nunca** apague a conta com `DELETE` direto: o apagamento em cascata dos contadores e o `SET NULL` das avaliações são feitos pelo código (BD-12). Use o comando `remover_conta`, que roda com o usuário da aplicação, dentro do container `backend` (não com o seu usuário MySQL) e **não pede confirmação**.

**A exclusão não tem desfazer.** Siga os passos nesta ordem.

**Passo 1. Confira que o `id` é da pessoa certa**, no `mysql`:

```sql
SELECT id, apelido, email_institucional, status, criado_em
FROM cadastro_usuario WHERE id = <conta_id>;
```

Compare com o pedido (apelido e e-mail institucional). Se não bater, pare.

**Passo 2. Suspenda a conta** ([operação 2](#_2-suspender-e-reativar-uma-conta)), para ela não criar avaliações enquanto você trabalha: uma avaliação criada depois do passo 4 e antes do comando ficaria sem dono e não poderia mais ser apagada a pedido do titular. Conta `pendente` não tem avaliações: pule este passo.

**Passo 3. Tire um backup à mão**, na VM (fora do `mysql`):

```bash
cd ~/2026-2-Bandejao-UnB
mkdir -p ~/backups
set -o pipefail
arq=~/backups/antes-remover-conta-$(date -u +%Y%m%dT%H%M%SZ).sql.gz
(umask 077 && docker compose exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot bandejao --single-transaction --routines --events --triggers' |
    gzip > "$arq") &&
    [ "$(zcat "$arq" | tail -n 1 | cut -c1-17)" = "-- Dump completed" ] &&
    echo "BACKUP OK: $arq" && ls -l "$arq" || echo "BACKUP FALHOU: não continue"
set +o pipefail
```

Só continue se aparecer `BACKUP OK`. Um dump vazio gera um arquivo `.gz` de poucos bytes, por isso a conferência é a última linha do dump, e não o tamanho.

**Este backup guarda os dados de quem pediu a exclusão.** Apague-o depois de conferir que a exclusão deu certo (passo 7) e, no máximo, em 7 dias, para cumprir o prazo do [aviso de privacidade](requisitos/aviso-de-privacidade.md). Os backups do deploy automático (`~/backups/deploy-*.sql.gz`, os 10 mais recentes, mais o `ultimo-ok.sql.gz`) são guardados por quantidade, e não por idade, então também podem passar de 7 dias: é uma limitação conhecida, tratada fora deste roteiro.

**Passo 4. Se o titular pediu que as avaliações dele também sejam apagadas** ([ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md), revisão de 14/11), apague-as **antes** do comando, porque depois dele o `usuario_id` das avaliações vira `NULL` e não dá mais para achá-las. No `mysql`:

```sql
ROLLBACK;
START TRANSACTION;
SELECT COUNT(*) FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;
DELETE FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;
SELECT COUNT(*) FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;  -- esperado: 0
-- se o último número for 0, digite: COMMIT;   senão: ROLLBACK;
```

Aqui o `COMMIT;` é **obrigatório** antes de sair do `mysql`: sem ele, o `DELETE` é desfeito sem aviso, e o comando do passo 5 anonimizaria as avaliações em vez de apagá-las. Depois do `COMMIT;`, abra uma **conexão nova** (saia do `mysql` e entre de novo) e confira que a contagem continua 0:

```sql
SELECT COUNT(*) FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>;  -- esperado: 0
```

Sem esse pedido do titular, pule este passo: as avaliações ficam e passam a aparecer como "usuário removido".

**Passo 5. Exclua a conta**, na VM:

```bash
cd ~/2026-2-Bandejao-UnB
docker compose exec backend python manage.py remover_conta <conta_id>
```

Na mesma transação, o comando apaga os contadores de gamificação (a conta sai do ranking), tira a conta e a hora exata dos registros de fila, encerra as sessões e apaga a conta com os tokens. A matrícula, o e-mail e o apelido ficam livres para um novo cadastro. Se a conta não existe, o comando termina com erro (`A conta <id> não existe.`) e nada muda. Rodar de novo numa conta já excluída dá o mesmo erro; a mensagem `... já foi excluída.` só aparece se duas exclusões rodarem ao mesmo tempo.

**Passo 6. Confira**, no `mysql`:

```sql
SELECT
  (SELECT COUNT(*) FROM cadastro_usuario WHERE id = <conta_id>) AS conta,
  (SELECT COUNT(*) FROM cadastro_token WHERE usuario_id = <conta_id>) AS tokens,
  (SELECT COUNT(*) FROM gamificacao_pontuacaousuario WHERE usuario_id = <conta_id>) AS pontos_totais,
  (SELECT COUNT(*) FROM gamificacao_pontossemestrecampus WHERE usuario_id = <conta_id>) AS pontos_semestre,
  (SELECT COUNT(*) FROM fila_checkin WHERE usuario_id = <conta_id>) AS checkins,
  (SELECT COUNT(*) FROM fila_tentativacheckin WHERE usuario_id = <conta_id>) AS tentativas,
  (SELECT COUNT(*) FROM avaliacao_avaliacao WHERE usuario_id = <conta_id>) AS avaliacoes;
-- esperado: tudo 0. As avaliações que o titular não pediu para apagar ficam no banco
-- com usuario_id vazio, então também não entram nesta contagem.
```

**Passo 7. Apague o backup do passo 3**, na VM, quando tudo estiver conferido:

Veja o nome exato do arquivo e apague só ele:

```bash
ls -l ~/backups/antes-remover-conta-*
rm -f -- ~/backups/antes-remover-conta-<data-do-backup>.sql.gz
```

Se você ainda está na mesma sessão do passo 3, `rm -f -- "$arq"` apaga o mesmo arquivo.

**Se algo der errado**, a volta é restaurar um backup, e ela traz o **banco inteiro**, não só esta conta: as outras contas e os pontos voltam ao estado da data do backup, e o que mudou depois se perde. Os backups do deploy (`deploy-*.sql.gz`) são do servidor todo (`--all-databases`). O guia do backup (`docs/deploy/backup-banco.md`, que entra com o BD-15) explica o procedimento de emergência. O backup diário de 7 dias (BD-15) só passa a valer quando estiver instalado na VM; até lá, conte só com os do deploy e com o que você tirou no passo 3.

## 4. Corrigir pontos

Quando: erro de pontuação (limitação L14: erros só se corrigem por ajuste manual) ou retirada de pontos de uma avaliação oculta. Há **duas** tabelas e as duas devem ficar coerentes: o total da conta e os pontos do semestre no campus.

**Antes, confira se a avaliação chegou a dar pontos.** Sem check-in na refeição, a avaliação não pontua:

```sql
SELECT a.id, a.usuario_id, a.pontos_concedidos_em, r.campus_id, r.data
FROM avaliacao_avaliacao a
JOIN cardapio_refeicao r ON r.id = a.refeicao_id
WHERE a.id = <id_da_avaliacao>;
```

Se `pontos_concedidos_em` da avaliação for `NULL`, ela nunca deu pontos: **não retire nada**. Se tiver data, anote o `campus_id` e a `data` da refeição: a linha certa de `gamificacao_pontossemestrecampus` é a desse campus e do **semestre dessa data**.

O semestre **não se deduz pelo mês**. O sistema coloca a data no primeiro semestre cujo término é igual ou posterior a ela, então as férias contam para o semestre seguinte. Os términos estão em `ParametrosGamificacaoConfig.datas_termino_semestre` (`backend/config/parametros.py`; hoje, `2026.2` termina em 14/12/2026). Exemplo: uma refeição de 20/12/2026 pontua em `2027.1`, e não em `2026.2`. Se a conta tiver mais de uma linha no campus, use a de `semestre_referencia` igual a esse semestre; tirar pontos da linha errada ainda dá "1 row affected".

`<n>` é o valor da contribuição: **avaliação 5**, check-in 10, resposta de saída 15 (`pontos_avaliacao`, `pontos_checkin` e `pontos_resposta_saida`, no mesmo arquivo; confira lá se mudaram). Na retirada de pontos de uma avaliação oculta, `<n>` é 5.

Para outros erros de pontuação, o marcador equivalente fica em `fila_checkin.pontos_concedidos_em` (check-in; o campus e a `data` da refeição estão na própria linha) e em `fila_perguntasaida.pontos_concedidos_em` (resposta de saída; a linha liga ao check-in por `checkin_id`). Se o marcador for `NULL`, não houve pontos a retirar. Casos que fogem disso se resolvem com a equipe.

```sql
ROLLBACK;
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

- Confira no primeiro `SELECT` da segunda tabela o campus e o semestre de cada linha, e use o `id` da linha certa, junto com o `usuario_id` da conta.
- Os pontos não podem ficar negativos (restrição `CHECK >= 0` nas duas tabelas). Se o primeiro `UPDATE` passar e o segundo falhar por isso, o total já foi mudado e a outra tabela não: digite `ROLLBACK;`. Por isso o `COMMIT` fica de fora.
- Tirar pontos de `pontos_totais` pode baixar a patente da conta.
- `atualizado_em` de `gamificacao_pontossemestrecampus` é o **desempate do ranking**. Corrigir pontos não deve mexer nele; só quem pontua muda esse campo.
- Se a conta não tem linha em `gamificacao_pontuacaousuario`, nada a corrigir.
- Para **devolver** pontos, use o mesmo bloco com `+ <n>`. Se faltar a linha do campus e do semestre, o segundo `UPDATE` afeta 0 linhas: faça `ROLLBACK;` e não crie a linha à mão, avise a equipe.

## 5. Matrícula contestada

Quando: alguém diz que uma conta foi criada com a matrícula ou o SIAPE dele (L01). O sistema não valida a matrícula contra a universidade, então a resolução é manual. A matrícula é guardada em texto claro ([ADR 0008](arquitetura/adr/0008-matricula-siape-em-texto-claro.md)). Quem contesta sabe a matrícula, e não o apelido: busque pela matrícula, que é única (`matricula_siape`).

```sql
SELECT id, apelido, matricula_siape, status, email_institucional, criado_em
FROM cadastro_usuario WHERE matricula_siape = '<matrícula>';
```

Se a busca vier vazia, nenhuma conta usa essa matrícula. Para achar pelo apelido (uma avaliação problemática, por exemplo), use `WHERE apelido_normalizado = '<apelido>'`: o `apelido` não é único; o que é único é o `apelido_normalizado`, que é o apelido sem acentos e em minúsculas.

Passos:

1. Peça ao contestante uma prova de que a matrícula é dele (o canal de contato do site) e compare com o e-mail institucional da conta.
2. Se a contestação procede: [suspenda a conta](#_2-suspender-e-reativar-uma-conta) e, depois, [exclua](#_3-excluir-uma-conta) se for o caso. Isso libera a matrícula para o titular real se cadastrar (`matricula_siape` é única). Se a conta estiver `pendente`, ela não pode ser suspensa: vá direto à exclusão.
3. Se não procede: responda ao contestante pelo canal de contato. Não há registro da decisão ([ADR 0004](arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md)).

Não envie a matrícula de uma conta a terceiros.

## Testar o roteiro sem mudar nada

Para ensaiar uma operação em produção, digite `ROLLBACK;` em vez de `COMMIT;` e confira o `SELECT` antes de sair. A exclusão de conta (operação 3) não tem `ROLLBACK`: ensaie só em ambiente de teste. A operação 5 só tem `SELECT` e não precisa de `ROLLBACK`.

## Quem tem acesso

Há duas portas, e a lista abaixo cobre as duas:

| Pessoa | Usuário MySQL | Papel | Acesso SSH à VM | Última conferência |
|---|---|---|---|---|
| Álvaro | `alvaro` | `equipe_moderacao` | sim | 24/11/2026 |
| Luís | `luis` | `equipe_moderacao` | sim | 24/11/2026 |

- **SSH:** é um único usuário, `azureuser`, com uma chave por pessoa em `~/.ssh/authorized_keys`, mais a chave do deploy automático (GitHub Actions), que não é de uma pessoa. Quem entra na VM e tem acesso ao Docker consegue ler a senha do `root` do MySQL ([Acesso da equipe](deploy/deploy-producao.md?id=acesso-da-equipe)). Por isso a chave SSH vale tanto quanto o usuário MySQL.
- **MySQL:** cada pessoa tem usuário próprio. O `root` é só para administração. A lista de usuários (`SELECT user, host FROM mysql.user;`) só se vê como `root` (o papel `equipe_moderacao` não lê essa tabela).

Hoje há dois usuários individuais; quem precisar moderar pede ao grupo para criar o seu (veja o deploy de produção). Quando alguém sair da equipe, no mesmo dia: remova a chave dela do `authorized_keys`, remova o usuário MySQL **e troque a senha do `root`** (quem esteve na VM pôde lê-la), e atualize a data da conferência. Sem isso, a lista envelhece em silêncio.
