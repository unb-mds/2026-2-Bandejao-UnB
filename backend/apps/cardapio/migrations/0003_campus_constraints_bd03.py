"""Impõe as invariantes dos raios e da confirmação dos campi."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = (("cardapio", "0002_campus_confirmacao_ativa"),)

    operations = (
        migrations.AddConstraint(
            model_name="campus",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(raio_confirmacao_metros__gte=0)
                    & models.Q(raio_deteccao_metros__gte=0)
                ),
                name="campus_raios_nao_negativos",
            ),
        ),
        migrations.AddConstraint(
            model_name="campus",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(confirmacao_ativa=False)
                    | models.Q(raio_confirmacao_metros__gt=0)
                ),
                name="campus_confirmacao_ativa_exige_raio_positivo",
            ),
        ),
    )
