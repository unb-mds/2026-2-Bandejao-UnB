"""Formatos de entrada e saída do app fila (contrato OpenAPI, BE-03)."""

from rest_framework import serializers

from apps.gamificacao.serializers import ResultadoPontuacaoSerializer


class CoordenadasSerializer(serializers.Serializer):
    """Posição do aparelho. Só existe no corpo do check-in (RI09, RF12)."""

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class CheckinEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/checkins/ (RF11, RF12, Fila N4 4a)."""

    campus = serializers.IntegerField(help_text="Id do campus (o de GET /api/campi/).")
    tipoRefeicao = serializers.CharField(
        help_text='Um de "cafe", "almoco" ou "jantar".',
    )
    coordenadas = CoordenadasSerializer()


class CheckinSerializer(serializers.Serializer):
    """O check-in confirmado. Nunca devolve coordenadas."""

    id = serializers.IntegerField()
    campus = serializers.IntegerField()
    tipoRefeicao = serializers.CharField()
    data = serializers.DateField()


class CheckinRegistradoSerializer(serializers.Serializer):
    """Resposta 201 do POST /api/checkins/: o check-in e os pontos."""

    checkin = CheckinSerializer()
    pontos = ResultadoPontuacaoSerializer()


class FaixaPrevistaSerializer(serializers.Serializer):
    """Uma faixa de 15 minutos da previsão (Fila N4 4c)."""

    inicio = serializers.TimeField(help_text="Horário local, America/Sao_Paulo.")
    fim = serializers.TimeField()
    nivel = serializers.CharField(
        help_text='Um de "vazia", "curta", "moderada" ou "longa".',
    )
    ehPico = serializers.BooleanField(
        help_text="true na faixa mais cheia (em empate, em todas elas).",
    )


class PrevisaoPicoSerializer(serializers.Serializer):
    """Resposta do GET /api/fila/previsao/ (Fila N4 4c). Só agregados."""

    campus = serializers.IntegerField()
    tipoRefeicao = serializers.CharField()
    data = serializers.DateField()
    status = serializers.CharField(
        help_text='"disponivel" ou "dados_insuficientes" (RF13).',
    )
    faixas = FaixaPrevistaSerializer(
        many=True,
        help_text="Vazia quando o status é dados_insuficientes.",
    )
