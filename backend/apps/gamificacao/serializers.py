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


class ProgressoSerializer(serializers.Serializer):
    """Resposta do GET /api/gamificacao/progresso/ (Gamificação N4 4c)."""

    patente = serializers.CharField(
        help_text=(
            'Um de "CALOURO_DE_BANDEJA", "RATO_DE_RU", "VETERANO", '
            '"MESTRE_DA_FILA" ou "LENDA_DO_RU" (RN11).'
        ),
    )
    pontosTotais = serializers.IntegerField()
    faltaParaProxima = serializers.IntegerField(
        help_text="Pontos que faltam para a próxima patente. 0 na última.",
    )
    sequencia = serializers.IntegerField(
        help_text="Semanas seguidas completadas (RN10).",
    )
    diasNaSemana = serializers.IntegerField(
        help_text="Dias com check-in na semana corrente.",
    )
    minimoDias = serializers.IntegerField(
        help_text="Dias necessários para completar a semana.",
    )
    participaRanking = serializers.BooleanField(
        help_text="Se a pessoa aderiu ao ranking (RF27.1).",
    )


class LinhaRankingPublicaSerializer(serializers.Serializer):
    """Uma linha do ranking. Só dados públicos (RI10, RI12)."""

    posicao = serializers.IntegerField()
    apelido = serializers.CharField()
    patente = serializers.CharField(
        help_text="Mesmos valores da patente de GET /api/gamificacao/progresso/.",
    )


class RankingPublicoSerializer(serializers.Serializer):
    """Resposta do GET /api/ranking/{campusId}/ (Gamificação N4 4c)."""

    campusId = serializers.IntegerField()
    semestre = serializers.CharField(help_text='Por exemplo "2026.2".')
    linhas = LinhaRankingPublicaSerializer(
        many=True,
        help_text="Até 10 linhas. Vazia se ninguém aderiu ainda (RF27.2).",
    )
