"""Formatos de entrada e saída do app fila (contrato OpenAPI, BE-03)."""

from rest_framework import serializers

from apps.cardapio.models import Campus, TipoRefeicao
from apps.fila.classificador_nivel_fila import NivelFila
from apps.gamificacao.serializers import ResultadoPontuacaoSerializer


class CoordenadasSerializer(serializers.Serializer):
    """Posição do aparelho. Só existe no corpo do check-in (RI09, RF12)."""

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class CheckinEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/checkins/ (RF11, RF12, Fila N4 4a)."""

    # Devolve o `Campus`; id inexistente é dado inválido. A mensagem do DRF
    # repete o id, mas a view responde com a mensagem fixa de `dados_invalidos`.
    campus = serializers.PrimaryKeyRelatedField(
        queryset=Campus.objects.all(),
        help_text="Id do campus (o de GET /api/campi/).",
    )
    tipoRefeicao = serializers.ChoiceField(choices=TipoRefeicao.choices)
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
    nivel = serializers.ChoiceField(
        choices=[nivel.value for nivel in NivelFila],
        help_text=(
            "Média da faixa contra a da faixa mais cheia: menos de 25% é "
            "vazia, menos de 50% curta, menos de 75% moderada, e o resto "
            "longa (RN06)."
        ),
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
        help_text=(
            '"disponivel" ou "dados_insuficientes" (RF13): o segundo com '
            "check-ins em menos de 3 dias distintos da janela."
        ),
    )
    faixas = FaixaPrevistaSerializer(
        many=True,
        help_text="Vazia quando o status é dados_insuficientes.",
    )
