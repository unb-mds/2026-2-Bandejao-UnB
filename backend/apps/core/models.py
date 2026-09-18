from django.db import models


class Campus(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class Dia(models.Model):
    DIAS_SEMANA = [
        ("SEG", "Segunda-feira"),
        ("TER", "Terça-feira"),
        ("QUA", "Quarta-feira"),
        ("QUI", "Quinta-feira"),
        ("SEX", "Sexta-feira"),
        ("SAB", "Sábado"),
    ]
    nome = models.CharField(max_length=3, choices=DIAS_SEMANA, unique=True)

    def __str__(self):
        return self.get_nome_display()