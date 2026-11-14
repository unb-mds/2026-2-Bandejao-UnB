"""Models do app `avaliacao`: AVALIACAO.

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(dicionário de dados e tabela "Constraints principais"), RF15, RNF07, RNF08.
"""

from django.conf import settings
from django.db import models
from django.db.models.functions import Length
from django.db.models.lookups import LessThanOrEqual

from apps.cardapio.models import Refeicao


class Avaliacao(models.Model):
    """Nota e comentário de uma conta sobre uma refeição inteira (RF15)."""

    # Nulo só se a linha de USUARIO for apagada fisicamente; na exclusão de
    # conta o RemoverContaCommand marca `status = removido` e o vínculo fica.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avaliacoes",
    )
    refeicao = models.ForeignKey(
        Refeicao, on_delete=models.CASCADE, related_name="avaliacoes"
    )
    nota = models.SmallIntegerField()
    comentario = models.TextField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    # A janela de edição (até 23h59 do mesmo dia) é validada na aplicação.
    editada_em = models.DateTimeField(null=True, blank=True)
    # Marcador de pontos já concedidos, preenchido pela Gamificação na primeira
    # vez que a avaliação pontua (ADR 0011, seção Consequências).
    pontos_concedidos_em = models.DateTimeField(null=True, blank=True)
    # Moderação manual pela equipe, por acesso direto ao banco (ADR 0004).
    oculta = models.BooleanField(default=False)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("usuario", "refeicao"),
                name="avaliacao_unica_por_usuario_refeicao",
            ),
            models.CheckConstraint(
                condition=models.Q(nota__gte=1, nota__lte=5),
                name="avaliacao_nota_entre_1_e_5",
            ),
            models.CheckConstraint(
                condition=models.Q(comentario__isnull=True)
                | LessThanOrEqual(Length("comentario"), 500),
                name="avaliacao_comentario_ate_500_caracteres",
            ),
        )

    def __str__(self):
        return f"Avaliação {self.nota} da refeição {self.refeicao_id}"
