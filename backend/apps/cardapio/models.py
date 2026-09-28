from django.db import models
from apps.core.models import Campus, Dia


class Cardapio(models.Model):
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="cardapios")
    dia = models.ForeignKey(Dia, on_delete=models.CASCADE, related_name="cardapios")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campus", "dia"],
                name="um_cardapio_por_campus_dia",
            )
        ]

    def __str__(self):
        return f"{self.campus} - {self.dia}"


class Prato(models.Model):
    TIPOS = [
        ("PRINCIPAL", "Prato principal"),
        ("ACOMPANHAMENTO", "Acompanhamento"),
        ("SOBREMESA", "Sobremesa"),
    ]

    cardapio = models.ForeignKey(Cardapio, on_delete=models.CASCADE, related_name="pratos")
    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"