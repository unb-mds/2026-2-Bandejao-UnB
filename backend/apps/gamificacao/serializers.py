"""Formatos de entrada e saída do app gamificacao (contrato OpenAPI, BE-03)."""

from rest_framework import serializers


class ResultadoPontuacaoSerializer(serializers.Serializer):
    """Bloco `pontos` devolvido por avaliação e check-in (Gamificação N4)."""

    total = serializers.IntegerField(
        help_text="Pontos desta resposta. 0: o PWA não mostra aviso (RF24.2).",
    )
    contribuicao = serializers.IntegerField(
        help_text="Parte do total que vem desta contribuição.",
    )
    avaliacaoLiberada = serializers.IntegerField(
        help_text="Parte do total vinda de uma avaliação liberada agora (RN09).",
    )
