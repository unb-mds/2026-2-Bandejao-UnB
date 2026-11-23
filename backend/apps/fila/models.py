"""Models do app `fila`: CHECKIN, TENTATIVA_CHECKIN, PERGUNTA_SAIDA e
RESPOSTA_SAIDA (Release 2).

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(dicionário de dados), RF11, RF12, RF21, RNF07, ADR 0011.
"""

from django.conf import settings
from django.db import models

from apps.cardapio.models import Campus, TipoRefeicao


class ResultadoTentativa(models.TextChoices):
    CONFIRMADO = "confirmado", "Confirmado"
    REJEITADO = "rejeitado", "Rejeitado"


class MotivoRejeicao(models.TextChoices):
    FORA_DO_HORARIO = "fora_do_horario", "Fora do horário"
    CHECKIN_DUPLICADO = "checkin_duplicado", "Check-in duplicado"
    LOCALIZACAO_NAO_CONFIRMADA = (
        "localizacao_nao_confirmada",
        "Localização não confirmada",
    )


class EstadoPergunta(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    RESPONDIDA = "respondida", "Respondida"
    DISPENSADA = "dispensada", "Dispensada"


class RespostaSaidaOpcao(models.TextChoices):
    SAI_ATE_5_MIN = "sai_ate_5_min", "Saio em até 5 min"
    SAI_5_A_10_MIN = "sai_5_a_10_min", "Saio entre 5 e 10 min"
    SAI_MAIS_DE_10_MIN = "sai_mais_de_10_min", "Saio em mais de 10 min"
    AINDA_NA_FILA = "ainda_na_fila", "Ainda estou na fila"
    DESISTI = "desisti", "Desisti"


class Checkin(models.Model):
    """Check-in confirmado. Não há FK para Refeicao: a refeição é identificada
    por campus + tipo + data, para a fila funcionar mesmo sem o cardápio.
    Dado pessoal (RNF07) enquanto ligado à conta."""

    # O vínculo é anulado após 4 semanas (RNF07.3, job de retenção do BD-11) e
    # na exclusão de conta (`RemoverContaCommand`); o `SET_NULL` cobre só a
    # exclusão física da linha de USUARIO.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkins",
    )
    campus = models.ForeignKey(
        Campus, on_delete=models.PROTECT, related_name="checkins"
    )
    tipo_refeicao = models.CharField(max_length=10, choices=TipoRefeicao.choices)
    data = models.DateField(db_index=True)
    # Apagada na retenção.
    registrado_em = models.DateTimeField(null=True, blank=True)
    # Início da faixa de 15 min, usado pela previsão de pico (RF13).
    faixa_inicio = models.TimeField()
    # Em minutos, uma casa decimal (RF22.1); gravado ao chegar a resposta (RN07).
    tempo_espera_min = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    # Marcador de pontos já concedidos (ADR 0011, seção Consequências).
    pontos_concedidos_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = (
            # NULL em `usuario` não colide no UNIQUE (SQLite e MySQL).
            models.UniqueConstraint(
                fields=("usuario", "campus", "tipo_refeicao", "data"),
                name="checkin_unico_por_usuario_campus_tipo_data",
            ),
        )
        indexes = (
            models.Index(
                fields=("campus", "tipo_refeicao", "data"),
                name="checkin_campus_tipo_data_idx",
            ),
        )

    def __str__(self):
        return f"{self.tipo_refeicao} de {self.data} ({self.campus_id})"


class TentativaCheckin(models.Model):
    """Toda tentativa de check-in, confirmada ou rejeitada (RF12). Sem UNIQUE.
    Dado pessoal (RNF07) enquanto ligado à conta."""

    # Mesma regra de retenção do `Checkin.usuario`: anulado pelo job de retenção
    # e na exclusão de conta; o `SET_NULL` cobre só a exclusão física.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tentativas_checkin",
    )
    campus = models.ForeignKey(
        Campus, on_delete=models.PROTECT, related_name="tentativas_checkin"
    )
    tipo_refeicao = models.CharField(max_length=10, choices=TipoRefeicao.choices)
    # Permanece depois que `data_hora` é apagada na retenção.
    data = models.DateField()
    data_hora = models.DateTimeField(null=True, blank=True)
    resultado = models.CharField(max_length=10, choices=ResultadoTentativa.choices)
    # Vazio quando `resultado = confirmado`.
    motivo = models.CharField(
        max_length=30, choices=MotivoRejeicao.choices, null=True, blank=True
    )

    class Meta:
        constraints = (
            # Confirmada não tem motivo; rejeitada tem sempre um motivo válido.
            models.CheckConstraint(
                condition=models.Q(
                    resultado=ResultadoTentativa.CONFIRMADO, motivo__isnull=True
                )
                | models.Q(
                    resultado=ResultadoTentativa.REJEITADO,
                    # `IN` com NULL dá NULL, que o CHECK aceita; por isso o
                    # `isnull=False` explícito.
                    motivo__isnull=False,
                    motivo__in=MotivoRejeicao.values,
                ),
                name="tentativa_motivo_coerente_com_resultado",
            ),
        )

    def __str__(self):
        return f"{self.resultado} em {self.data} ({self.campus_id})"


class PerguntaSaida(models.Model):
    """Pergunta de saída gerada por cada check-in confirmado (RF21). Dado
    pessoal (RNF07) enquanto o check-in estiver ligado à conta."""

    checkin = models.OneToOneField(
        Checkin, on_delete=models.CASCADE, related_name="pergunta_saida"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPergunta.choices,
        default=EstadoPergunta.PENDENTE,
    )
    # Vez em que a pergunta é exibida: 1 ou 2 (2 = repetição depois de "Ainda
    # estou na fila"). Não tem relação com `TentativaCheckin`.
    tentativa = models.SmallIntegerField(default=1)
    # Check-in + 15 min (Anexo A).
    devida_em = models.DateTimeField()
    # Check-in + 60 min; a expiração é avaliada na consulta, sem cron.
    expira_em = models.DateTimeField()
    # Marcador de pontos já concedidos (ADR 0011, seção Consequências).
    pontos_concedidos_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = (
            models.CheckConstraint(
                condition=models.Q(tentativa__in=(1, 2)),
                name="pergunta_saida_tentativa_1_ou_2",
            ),
        )
        indexes = (
            models.Index(
                fields=("estado", "devida_em"),
                name="pergunta_estado_devida_idx",
            ),
        )

    def __str__(self):
        return f"Pergunta {self.estado} do check-in {self.checkin_id}"


class RespostaSaida(models.Model):
    """Resposta à pergunta de saída; a segunda só existe depois de "Ainda estou
    na fila". Não guarda a conta: chega a ela pela pergunta e pelo check-in.
    Dado pessoal (RNF07) enquanto o check-in estiver ligado à conta."""

    pergunta = models.ForeignKey(
        PerguntaSaida, on_delete=models.CASCADE, related_name="respostas"
    )
    # Vez da pergunta a que esta resposta se refere: 1 ou 2.
    tentativa = models.SmallIntegerField()
    resposta = models.CharField(max_length=20, choices=RespostaSaidaOpcao.choices)
    respondida_em = models.DateTimeField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("pergunta", "tentativa"),
                name="resposta_saida_unica_por_pergunta_tentativa",
            ),
            models.CheckConstraint(
                condition=models.Q(tentativa__in=(1, 2)),
                name="resposta_saida_tentativa_1_ou_2",
            ),
        )

    def __str__(self):
        return f"{self.resposta} (tentativa {self.tentativa})"
