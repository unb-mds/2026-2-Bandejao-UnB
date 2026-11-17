"""Tabela do cache em banco (#123).

O `DatabaseCache` (contadores do limite de taxa) precisa da tabela
`cache_bandejao`, que não é model: o `migrate` sozinho não a cria, e sem ela
todo login, cadastro e reenvio daria 500. Esta migration chama o
`createcachetable`, para a tabela nascer em todo lugar que roda o `migrate`
(runserver de cada um, CI e deploy). O comando não faz nada se ela já existe.
"""

from django.core.management import call_command
from django.db import migrations


def criar_tabela_do_cache(apps, schema_editor):
    call_command("createcachetable", database=schema_editor.connection.alias)


class Migration(migrations.Migration):
    dependencies = [("cadastro", "0002_usuario_primeira_falha_login_em")]

    operations = [
        migrations.RunPython(criar_tabela_do_cache, migrations.RunPython.noop),
    ]
