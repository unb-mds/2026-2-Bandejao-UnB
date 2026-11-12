"""Models do app `gamificacao`: PONTUACAO_USUARIO e PONTOS_SEMESTRE_CAMPUS
(Release 2).

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(dicionário de dados), RN09, RN10, RN12, ADR 0011.

`posicao_final` (N4) fica de fora, conforme o backlog (BD-01): quando o
fechamento do semestre for implementado, entra por uma migration simples.
"""

from django.conf import settings
from django.db import models

from apps.cardapio.models import Campus


class PontuacaoUsuario(models.Model):
    """Contadores de gamificação da conta. A patente é derivada, não coluna.
    Dado pessoal (RNF07)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pontuacao",
    )
    pontos_totais = models.IntegerField(default=0)
    sequencia_atual = models.IntegerField(default=0)
    # Segunda-feira da semana.
    ultima_semana_completada = models.DateField(null=True, blank=True)
    # Adesão ao ranking (RN12).
    participa_ranking = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = (
            models.CheckConstraint(
                condition=models.Q(pontos_totais__gte=0),
                name="pontuacao_pontos_totais_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(sequencia_atual__gte=0),
                name="pontuacao_sequencia_atual_nao_negativa",
            ),
        )

    def __str__(self):
        return f"{self.pontos_totais} pontos (usuário {self.usuario_id})"


class PontosSemestreCampus(models.Model):
    """Uma linha por conta, campus e semestre (nada zera na virada)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pontos_semestre_campus",
    )
    campus = models.ForeignKey(
        Campus, on_delete=models.PROTECT, related_name="pontos_semestre"
    )
    # Ex.: "2026.2".
    semestre_referencia = models.CharField(max_length=10)
    pontos = models.IntegerField(default=0)
    # Desempate do ranking.
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("usuario", "campus", "semestre_referencia"),
                name="pontos_semestre_unico_por_usuario_campus_semestre",
            ),
            models.CheckConstraint(
                condition=models.Q(pontos__gte=0),
                name="pontos_semestre_pontos_nao_negativo",
            ),
        )
        indexes = (
            models.Index(
                fields=("campus", "semestre_referencia", "-pontos", "atualizado_em"),
                name="pontos_semestre_ranking_idx",
            ),
        )

    def __str__(self):
        return f"{self.pontos} pontos em {self.semestre_referencia}"
