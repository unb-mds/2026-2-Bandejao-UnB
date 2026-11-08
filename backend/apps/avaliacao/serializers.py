"""Formatos de entrada e saída do app avaliacao (contrato OpenAPI, BE-03)."""

from rest_framework import serializers

from apps.gamificacao.serializers import ResultadoPontuacaoSerializer


class AvaliacaoEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/avaliacoes/ (RF15, Avaliação N4 4a)."""

    refeicaoId = serializers.IntegerField(help_text="Id da refeição avaliada.")
    nota = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Obrigatória, de 1 a 5.",
    )
    comentario = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Opcional, até 500 caracteres.",
    )


class AvaliacaoSerializer(serializers.Serializer):
    """A avaliação gravada. Só os campos do próprio autor."""

    id = serializers.IntegerField()
    refeicaoId = serializers.IntegerField()
    nota = serializers.IntegerField()
    comentario = serializers.CharField(allow_blank=True)
    criadaEm = serializers.DateTimeField()
    editadaEm = serializers.DateTimeField(
        allow_null=True,
        help_text="null se a avaliação nunca foi editada.",
    )


class AvaliacaoRegistradaSerializer(serializers.Serializer):
    """Resposta do POST /api/avaliacoes/: a avaliação e os pontos."""

    avaliacao = AvaliacaoSerializer()
    pontos = ResultadoPontuacaoSerializer()


class AvaliacaoPublicaSerializer(serializers.Serializer):
    """Um comentário público (Avaliação N4 4b). Só dados do autor já públicos."""

    apelido = serializers.CharField(
        help_text="Apelido do autor, ou `usuário removido` se a conta foi removida.",
    )
    nota = serializers.IntegerField()
    comentario = serializers.CharField(allow_blank=True)
    criadaEm = serializers.DateTimeField()


class ResumoAvaliacoesSerializer(serializers.Serializer):
    """Nota média e quantidade de avaliações de uma refeição."""

    media = serializers.FloatField(
        allow_null=True,
        help_text="null enquanto não há avaliações.",
    )
    quantidade = serializers.IntegerField()


class AvaliacoesDaRefeicaoSerializer(serializers.Serializer):
    """Resposta do GET /api/refeicoes/{refeicaoId}/avaliacoes/."""

    resumoAvaliacoes = ResumoAvaliacoesSerializer()
    comentarios = AvaliacaoPublicaSerializer(many=True)


class ResumoRefeicaoSerializer(serializers.Serializer):
    """Uma refeição no resumo do dia (Avaliação N4 4b)."""

    refeicaoId = serializers.IntegerField()
    tipo = serializers.CharField(help_text='Um de "cafe", "almoco" ou "jantar".')
    media = serializers.FloatField(
        allow_null=True,
        help_text="null enquanto não há avaliações.",
    )
    quantidade = serializers.IntegerField()
