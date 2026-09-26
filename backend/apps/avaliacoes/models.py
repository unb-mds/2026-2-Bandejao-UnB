from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Avaliacao(models.Model):
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.CASCADE, related_name="avaliacoes"
    )
    prato = models.ForeignKey(
        "cardapio.Prato", on_delete=models.CASCADE, related_name="avaliacoes"
    )
    nota = models.PositiveSmallIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
)
    comentario = models.TextField(blank=True, null=True)
    data = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "prato", "data"],
                name="uma_avaliacao_por_usuario_prato_dia",
            )
        ]

    def __str__(self):
        return f"{self.usuario} - {self.prato} ({self.data}): {self.nota}"