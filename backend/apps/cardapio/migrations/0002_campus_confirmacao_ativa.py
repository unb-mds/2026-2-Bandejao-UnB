"""Permite configurar a confirmação de localização por campus."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = (("cardapio", "0001_initial"),)

    operations = (
        migrations.AddField(
            model_name="campus",
            name="confirmacao_ativa",
            field=models.BooleanField(default=True),
        ),
    )
