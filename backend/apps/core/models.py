from django.db import models


class Campus(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class Dia(models.Model):
    """
    Dia da semana do cardápio (recorrente).
    Não confundir com o campo `data` de Avaliacao, que é a data real
    em que o prato foi servido/avaliado.
    """
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