"""PROVA DESCARTÁVEL do #209: NÃO MESCLAR.

Cria um TRIGGER no MySQL, o que exige o privilégio TRIGGER, fora da lista do
db/init/10-usuarios.sh. Com o usuário restrito no CI, o migrate tem que
falhar com acesso negado.
"""

from django.db import migrations


def criar_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute(
        "CREATE TRIGGER prova_209 BEFORE INSERT ON fila_checkin "
        "FOR EACH ROW SET NEW.tempo_espera_min = NEW.tempo_espera_min"
    )


class Migration(migrations.Migration):
    dependencies = [("fila", "0001_initial")]

    operations = [migrations.RunPython(criar_trigger, migrations.RunPython.noop)]
