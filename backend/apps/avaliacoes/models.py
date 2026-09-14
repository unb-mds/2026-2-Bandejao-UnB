# Alinhado com Luís: FK para usuarios.Usuario e cardapio.Prato.
# Observação (RF06): Prato deve ter FK para Campus e Dia.

from django.db import models


class Avaliacao(models.Model):
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.CASCADE, related_name="avaliacoes"
    )
    prato = models.ForeignKey(
        "cardapio.Prato", on_delete=models.CASCADE, related_name="avaliacoes"
    )
    nota = models.PositiveSmallIntegerField()  # range 1-5 validado no RF16 (Sprint 4)
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