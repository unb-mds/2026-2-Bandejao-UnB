# Backup do banco de produção (BD-15)

O banco de produção (MySQL 8.4, no container `db` da VM) tem **uma cópia por
dia, guardada por 7 dias** (Anexo A). Passado o prazo, a cópia é apagada, para
que os dados de uma conta excluída também saiam dos backups (RNF07.4). O
acesso é o mesmo do banco: só quem entra na VM pelo SSH (ADR 0004 e 0008).

Os arquivos ficam em `deploy/backup/`:

| Arquivo | Vai para | O que faz |
|---|---|---|
| `backup-banco.sh` | (fica no repositório) | `mysqldump` consistente do banco, conferido e comprimido, com a rotação de 7 dias |
| `testar-restauracao.sh` | (fica no repositório) | Sobe um MySQL temporário, restaura uma cópia e compara com a produção |
| `bandejao-backup` | `/etc/cron.d/bandejao-backup` | Roda o backup todo dia, às 03h45 de Brasília (06h45 UTC), depois da retenção da fila (03h30, BD-11, no cron do BD-07) |

## Como funciona

- O dump é feito **dentro do container `db`**, com `--single-transaction`
  (sem travar o app), rotinas e gatilhos, em `utf8mb4`. A senha do root vem do
  ambiente do container (`.env.db`) e vai ao `mysqldump` pela variável
  `MYSQL_PWD`, e não como argumento: não passa pelo script nem aparece na
  lista de processos do host.
- O arquivo só ganha o nome final (`bandejao-AAAAMMDDTHHMMSSZ.sql.gz`) depois
  de conferido: o `gzip` íntegro e a última linha do dump
  (`-- Dump completed`). Um dump pela metade nunca vira backup.
- As cópias ficam em `/var/backups/bandejao`, com permissão `600`, numa pasta
  `700` do `azureuser`.
- **Rotação:** antes de cada dump, o script apaga as cópias com mais de 7 dias.
  O corte é de 6 dias e 22 h, e não de 7 dias redondos, porque o cron roda
  sempre no mesmo horário, mas o arquivo ganha a data com alguns segundos de
  atraso: sem a folga, a cópia de 7 dias atrás ainda estaria ali e a pasta
  teria 8 cópias. Ela roda **mesmo que o dump falhe**: o prazo da LGPD vale
  mais que ter uma cópia. Com um backup por dia, a pasta fica com 7 cópias
  (cada backup feito à mão soma mais uma, até a próxima rotação).
- **Tempo limite:** o dump roda com `timeout` de 30 min **dentro do container
  `db`** (o `mysqldump` morre junto) e outro de 35 min no cliente, no host. O
  log traz uma mensagem própria para o tempo esgotado (status 124) e para o
  processo morto com KILL (137).
- **Log e avisos:** o script grava o próprio log em
  `/var/log/bandejao/backup-banco.log` (girado pelo mesmo `logrotate` do cron,
  BD-07) e testa a escrita antes de começar, como o `rodar-comando.sh`: a linha
  do cron não tem redireção, para o cron não parar em silêncio se o log não
  abrir. Sem permissão de escrita no log ou na trava, o script sai com 73 e
  avisa o syslog (a rotação das cópias velhas roda **antes** desse teste, então
  continua valendo, e o `crit` abaixo também vale para essa saída e para a do
  backup "pulado", status 75). Erros **e o resumo de cada execução** vão também para o
  syslog, com a tag `bandejao-backup` (`journalctl -t bandejao-backup`),
  porque a VM não manda e-mail.
- **Pasta sem backup útil:** como a rotação roda mesmo com o dump falhando,
  7 falhas seguidas (uma senha trocada no `.env.db`, por exemplo) apagam todas
  as cópias. Quando uma falha deixa a pasta sem cópia, ou com a mais nova com
  mais de 26 h, o script grava um aviso `user.crit` no syslog. Confira com
  `journalctl -t bandejao-backup -p err`, que traz o `crit` **e** os erros
  comuns (`-p crit` sozinho esconde a falha com status 73). Se o arquivo novo tiver menos da
  metade do tamanho da cópia anterior (um banco que perdeu os dados vira um
  dump completo e pequeno), o aviso é `user.warning`.
- **Interrupção:** o `sh` não roda a limpeza sozinho num sinal, então o script
  converte Ctrl-C, `kill` e o TERM do systemd em saída com status 130, apaga o
  dump em andamento e registra "interrompido por sinal" no log e no syslog.
  Duas limitações: um `kill <pid>` só no script não é imediato (o `sh` espera o
  `timeout` filho terminar, até cerca de 35 min; só o Ctrl-C atinge o grupo
  inteiro), e, depois do Ctrl-C, o `mysqldump` continua dentro do container até
  terminar ou até o limite de 30 min. A trava é liberada, então um backup
  logo em seguida roda em paralelo com ele.
- **Tabela de cache fora:** a `cache_bandejao` (limite de taxa, com chaves que
  podem ter IP) é efêmera e fica fora do dump. Depois de restaurar num banco
  **vazio**, rode `docker compose exec backend python manage.py
  createcachetable`.

## Instalar (uma vez, na VM, como `azureuser`)

Depois de atualizar o repositório da VM (`git pull`, ver
[Atualizar](deploy/deploy-producao.md?id=atualizar)):

```bash
cd ~/2026-2-Bandejao-UnB
sudo install -d -m 700 -o azureuser -g azureuser /var/backups/bandejao
sudo install -m 644 -o root -g root deploy/backup/bandejao-backup /etc/cron.d/bandejao-backup
```

Este guia pressupõe o cron do BD-07 instalado (a pasta `/var/log/bandejao` e o
`logrotate`, ver [Tarefas periódicas](deploy/deploy-producao.md?id=tarefas-periódicas-cron)).
Antes do primeiro dia, confira que o container `db` tem o `timeout`:
`docker compose exec -T db timeout --version`.

Rode o primeiro backup à mão, **sem `sudo`**:

```bash
cd ~/2026-2-Bandejao-UnB
sh deploy/backup/backup-banco.sh
tail -n 3 /var/log/bandejao/backup-banco.log
ls -la /var/backups/bandejao
```

O esperado é uma linha `ok: bandejao-....sql.gz` no fim do log, um arquivo
`-rw-------` e a pasta `.` com `drwx------`.

Com `sudo`, a cópia nova nasce do root e, **se ainda não existiam**, o `.trava`
e o log também (o `>>` não troca o dono de um arquivo que já existe). A pasta
continua do `azureuser`. Quando o log ou a trava passam a ser do root, o cron
seguinte sai com status 73 e avisa o syslog (as cópias velhas ainda saem, e o
aviso `crit` aparece se a pasta ficar sem cópia útil). Para desfazer:

```bash
sudo rm -f /var/backups/bandejao/.trava
sudo chown azureuser: /var/log/bandejao/backup-banco.log /var/backups/bandejao/*
```

## Testar a restauração (BD-15 pede uma vez)

```bash
sh deploy/backup/testar-restauracao.sh
```

O script usa a cópia mais recente (ou a que você passar como argumento), sobe
um MySQL temporário **sem rede** e com senha aleatória, restaura e compara:
o número de tabelas (sem a de cache) tem que ser o da produção, o
`django_migrations` não pode estar vazio e o `cadastro_usuario` não pode estar
vazio nem ter menos da metade das contas da produção: um banco recriado gera
um dump completo e sem contas, que não pode passar como backup bom. (Uma
tabela qualquer com linhas não basta: a de cache enche com uma tentativa de
login.) Se uma consulta falhar, o erro do MySQL
aparece na mensagem. Termina com `OK: a restauração de ... foi conferida.` O
container temporário (e o volume dele) some sozinho, inclusive num Ctrl-C. A
senha dele não aparece no `ps`. O banco de produção só é lido.

Anote o dia e o resultado em
[Validação em produção](deploy/deploy-producao.md?id=validação-em-produção-20112026).

## Conferir a rotação

```bash
ls -la --time-style=long-iso /var/backups/bandejao
```

Depois de uma semana, as datas devem ser as 7 últimas, e a mais antiga não
pode ter mais de 7 dias. O log (`/var/log/bandejao/backup-banco.log`) mostra,
a cada dia, quantas cópias ficaram. No dia seguinte à instalação, confira
também `journalctl -t bandejao-backup -p err` e que **não** há linha `crit`
(o `-p err` inclui o `crit`).

## Restaurar de verdade (emergência)

Só com o backend parado, para ninguém gravar durante a restauração. O dump
traz `DROP TABLE IF EXISTS`, então ele **substitui** as tabelas atuais. As
cópias se chamam `bandejao-AAAAMMDDTHHMMSSZ.sql.gz` (data em UTC):

```bash
cd ~/2026-2-Bandejao-UnB
ls /var/backups/bandejao
docker compose stop backend
gzip -dc /var/backups/bandejao/bandejao-<data>.sql.gz | docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot bandejao'
docker compose start backend
```

Tabelas criadas **depois** do backup não fazem parte do dump e continuam no
banco; uma migration que as cria falharia com "already exists". Se isso
acontecer, recrie o banco antes de restaurar (`DROP DATABASE bandejao;` e
`CREATE DATABASE bandejao CHARACTER SET utf8mb4;`, pelo `mysql` do container
`db`) e restaure de novo. Ensaie antes com o `testar-restauracao.sh`, que não
toca na produção.

## Limites conhecidos

- As cópias ficam **no disco da mesma VM**. Elas protegem de erro de dado e de
  um `docker compose down -v`, mas **não** de perder a VM ou o disco. O
  [ADR 0012](arquitetura/adr/0012-hospedagem-e-servico-de-email.md) prevê
  o backup diário guardado **fora da VM**; por ora ele não existe, e a cópia
  externa fica como evolução, fora do escopo do BD-15. Quando vier, tem que
  respeitar os mesmos 7 dias.
- O backup lê o banco no instante do dump. Um registro apagado depois (exclusão
  de conta, BD-12) continua nas cópias já feitas por até 7 dias, e é isso que
  o aviso de privacidade deve dizer.
- O disco da VM é pequeno (cerca de 28 GB). Confira o tamanho das cópias
  (`du -sh /var/backups/bandejao`) quando houver dados reais. Durante o
  backup, o dump sem compressão ocupa o disco antes do `gzip`, então o pico é
  de cerca do dobro do tamanho do dump, além das 7 cópias.
