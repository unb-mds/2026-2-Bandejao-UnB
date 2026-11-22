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
| `bandejao-backup` | `/etc/cron.d/bandejao-backup` | Roda o backup todo dia, às 03h45 de Brasília (06h45 UTC), depois da retenção da fila (03h30, BD-07) |

## Como funciona

- O dump é feito **dentro do container `db`**, com `--single-transaction`
  (sem travar o app), rotinas e gatilhos, em `utf8mb4`. A senha do root vem do
  ambiente do container (`.env.db`) e não passa pelo script nem aparece na
  lista de processos do host.
- O arquivo só ganha o nome final (`bandejao-AAAAMMDDTHHMMSSZ.sql.gz`) depois
  de conferido: o `gzip` íntegro e a última linha do dump
  (`-- Dump completed`). Um dump pela metade nunca vira backup.
- As cópias ficam em `/var/backups/bandejao`, com permissão `600`, numa pasta
  `700` do `azureuser`.
- **Rotação:** antes de cada dump, o script apaga as cópias com mais de 7 dias
  (6 dias e 22 h, para a folga do cron). Ela roda **mesmo que o dump falhe**:
  o prazo da LGPD vale mais que ter uma cópia. Com um backup por dia, a pasta
  nunca passa de 7 cópias.
- Falhas vão para o syslog com a tag `bandejao-backup`
  (`journalctl -t bandejao-backup`), porque a VM não manda e-mail. O resumo de
  cada execução fica em `/var/log/bandejao/backup-banco.log`, girado pelo
  mesmo `logrotate` do cron (BD-07).

## Instalar (uma vez, na VM, como `azureuser`)

Depois de atualizar o repositório da VM (`git pull`, ver
[Atualizar](deploy-producao.md#atualizar)):

```bash
cd ~/2026-2-Bandejao-UnB
sudo install -d -m 700 -o azureuser -g azureuser /var/backups/bandejao
sudo install -m 644 -o root -g root deploy/backup/bandejao-backup /etc/cron.d/bandejao-backup
```

Rode o primeiro backup à mão, sem `sudo` (com `sudo`, a pasta e o log passam a
ser do root e o cron do `azureuser` deixa de gravar):

```bash
sh deploy/backup/backup-banco.sh
ls -l /var/backups/bandejao
```

O esperado é uma linha `ok: bandejao-....sql.gz`, um arquivo `-rw-------` e a
pasta `drwx------`.

## Testar a restauração (BD-15 pede uma vez)

```bash
sh deploy/backup/testar-restauracao.sh
```

O script usa a cópia mais recente (ou a que você passar como argumento), sobe
um MySQL temporário **sem rede** e com senha aleatória, restaura e compara:
o número de tabelas tem que ser o da produção, e o `django_migrations` não
pode estar vazio. Termina com `OK: a restauração de ... foi conferida.` O
container temporário some sozinho. O banco de produção só é lido.

Anote o dia e o resultado em
[Validação em produção](deploy-producao.md#validação-em-produção-20112026).

## Conferir a rotação

```bash
ls -l --time-style=long-iso /var/backups/bandejao
```

Depois de uma semana, as datas devem ser as 7 últimas, e a mais antiga não
pode ter mais de 7 dias. O log (`/var/log/bandejao/backup-banco.log`) mostra,
a cada dia, quantas cópias ficaram.

## Restaurar de verdade (emergência)

Só com o backend parado, para ninguém gravar durante a restauração. O dump
traz `DROP TABLE IF EXISTS`, então ele **substitui** as tabelas atuais:

```bash
docker compose stop backend
gzip -dc /var/backups/bandejao/bandejao-<data>.sql.gz | docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" bandejao'
docker compose start backend
```

Ensaie antes com o `testar-restauracao.sh`, que não toca na produção.

## Limites conhecidos

- As cópias ficam **no disco da mesma VM**. Elas protegem de erro de dado e de
  um `docker compose down -v`, mas **não** de perder a VM ou o disco. Cópia
  fora da VM seria uma decisão nova (e teria que respeitar os mesmos 7 dias).
- O backup lê o banco no instante do dump. Um registro apagado depois (exclusão
  de conta, BD-12) continua nas cópias já feitas por até 7 dias, e é isso que
  o aviso de privacidade deve dizer.
- O disco da VM é pequeno (cerca de 28 GB). Confira o tamanho das cópias
  (`du -sh /var/backups/bandejao`) quando houver dados reais.
