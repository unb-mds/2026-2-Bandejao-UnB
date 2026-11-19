"""Origem do cardápio de cada campus (ADR 0014, BD-16).

1. Acrescenta `rotulo_pagina_ru` e `prefixo_arquivo_pdf` em `CAMPUS`, ainda
   aceitando nulo.
2. Preenche as duas colunas nos campi que já existem: os 5 do Anexo A pelo
   nome; qualquer outro recebe marcadores pelo id ("sem-rotulo-<id>",
   "sem-prefixo-<id>"), que não colidem com os valores do Anexo A nem batem
   com título ou arquivo da página do RU. O nome não serve de reserva: um
   campus "Fazenda" colidiria com o prefixo da Fazenda Água Limpa, e, no
   MySQL, cuja collation ignora acentos e maiúsculas, as colisões seriam
   ainda mais fáceis. O valor certo vem da fixture `campi`.
3. Torna as colunas NOT NULL e UNIQUE.
4. Cria `FONTE_CARDAPIO`.
"""

import django.db.models.deletion
from django.db import migrations, models

# Rótulo na página do RU e prefixo do arquivo, por nome do campus (Anexo A).
ORIGEM_POR_NOME = {
    "Darcy Ribeiro": ("Darcy Ribeiro", "Darcy-Ribeiro"),
    "Ceilândia": ("Ceilândia", "Ceilandia"),
    "Gama": ("Gama", "Gama"),
    "Planaltina": ("Planaltina", "Planaltina"),
    "Fazenda Água Limpa": ("Fazenda Água Limpa", "Fazenda"),
}


def preencher_origem(apps, schema_editor):
    campus = apps.get_model("cardapio", "Campus")
    for registro in campus.objects.using(schema_editor.connection.alias).all():
        rotulo, prefixo = ORIGEM_POR_NOME.get(
            registro.nome,
            (f"sem-rotulo-{registro.pk}", f"sem-prefixo-{registro.pk}"),
        )
        registro.rotulo_pagina_ru = rotulo
        registro.prefixo_arquivo_pdf = prefixo
        registro.save(update_fields=["rotulo_pagina_ru", "prefixo_arquivo_pdf"])


class Migration(migrations.Migration):
    dependencies = (("cardapio", "0003_campus_constraints_bd03"),)

    operations = (
        migrations.AddField(
            model_name="campus",
            name="rotulo_pagina_ru",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="campus",
            name="prefixo_arquivo_pdf",
            field=models.CharField(max_length=50, null=True),
        ),
        # Na volta, as colunas são removidas pelo AddField; não há o que
        # desfazer aqui.
        migrations.RunPython(preencher_origem, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="campus",
            name="rotulo_pagina_ru",
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name="campus",
            name="prefixo_arquivo_pdf",
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.CreateModel(
            name="FonteCardapio",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("semana_inicio", models.DateField()),
                ("url", models.URLField(max_length=500)),
                ("sha256", models.CharField(max_length=64)),
                ("verificado_em", models.DateTimeField()),
                ("processado_em", models.DateTimeField()),
                (
                    "campus",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fontes_cardapio",
                        to="cardapio.campus",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("campus", "semana_inicio"),
                        name="fonte_cardapio_unica_por_campus_semana",
                    )
                ],
            },
        ),
    )
