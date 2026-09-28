from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Campus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Dia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(
                    choices=[
                        ('SEG', 'Segunda-feira'),
                        ('TER', 'Terça-feira'),
                        ('QUA', 'Quarta-feira'),
                        ('QUI', 'Quinta-feira'),
                        ('SEX', 'Sexta-feira'),
                        ('SAB', 'Sábado'),
                    ],
                    max_length=3,
                    unique=True,
                )),
            ],
        ),
    ]
