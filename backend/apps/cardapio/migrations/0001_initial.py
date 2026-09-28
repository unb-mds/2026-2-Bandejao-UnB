import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cardapio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('campus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cardapios', to='core.campus')),
                ('dia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cardapios', to='core.dia')),
            ],
        ),
        migrations.AddConstraint(
            model_name='cardapio',
            constraint=models.UniqueConstraint(fields=('campus', 'dia'), name='um_cardapio_por_campus_dia'),
        ),
        migrations.CreateModel(
            name='Prato',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('tipo', models.CharField(
                    choices=[
                        ('PRINCIPAL', 'Prato principal'),
                        ('ACOMPANHAMENTO', 'Acompanhamento'),
                        ('SOBREMESA', 'Sobremesa'),
                    ],
                    max_length=20,
                )),
                ('descricao', models.TextField(blank=True, null=True)),
                ('cardapio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pratos', to='cardapio.cardapio')),
            ],
        ),
    ]