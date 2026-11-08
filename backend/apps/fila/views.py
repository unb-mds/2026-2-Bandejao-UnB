"""Views do app fila (entram nas histórias de usuário)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.fila.serializers import (
    CheckinEntradaSerializer,
    CheckinRegistradoSerializer,
    PrevisaoPicoSerializer,
)
from config.erros import ErroSerializer


class CheckinView(APIView):
    """POST /api/checkins/ (RF11, RF12, Fila N4 4a). Lógica em outra BE.

    Sem permission_classes de propósito: o padrão do projeto já exige login.
    """

    @extend_schema(
        summary="Registra o check-in no RU, com confirmação por GPS",
        description=(
            "As coordenadas só viajam no corpo desta requisição: nunca em "
            "query string e nunca em resposta, e o servidor não as grava "
            "(RI09, RF12). Campus e refeição da pontuação são os do próprio "
            "check-in, nunca um campo enviado pelo front (RN09)."
        ),
        tags=["fila"],
        request=CheckinEntradaSerializer,
        responses={
            201: CheckinRegistradoSerializer,
            401: OpenApiResponse(
                ErroSerializer,
                description="Sem sessão. `codigo`: `nao_autenticado`.",
            ),
            403: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Falta dar ciência ao aviso de privacidade atualizado "
                    "(RF11). `codigo`: `aviso_privacidade_pendente`."
                ),
            ),
            422: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Check-in recusado. `codigo`: `fora_do_horario` (fora da "
                    "janela da refeição), `checkin_duplicado` (já existe "
                    "check-in desta conta na mesma refeição, RI03) ou "
                    "`localizacao_nao_confirmada` (fora do raio do RU)."
                ),
            ),
        },
    )
    def post(self, request):
        # Só contrato: a lógica (CheckinService) vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class PrevisaoView(APIView):
    """GET /api/fila/previsao/ (RF13, Fila N4 4c)."""

    # Público: devolve só agregados, nada de conta ou check-in individual.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Previsão de pico por faixa de horário",
        description=(
            "Calculada sob demanda a partir dos check-ins das últimas 4 "
            "semanas, no mesmo dia da semana (RF13). Com poucos dados volta "
            "200 com `status` igual a `dados_insuficientes`, e não erro."
        ),
        tags=["fila"],
        parameters=[
            OpenApiParameter(
                "campus",
                int,
                OpenApiParameter.QUERY,
                required=True,
                description="Id do campus (o de GET /api/campi/).",
            ),
            OpenApiParameter(
                "refeicao",
                str,
                OpenApiParameter.QUERY,
                required=True,
                enum=["cafe", "almoco", "jantar"],
                description="Refeição da previsão.",
            ),
            OpenApiParameter(
                "data",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                description="Dia da previsão. Omitido: dia corrente.",
            ),
        ],
        responses={
            200: PrevisaoPicoSerializer,
            400: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Parâmetro ausente ou inválido, como `campus`. "
                    "`codigo`: `parametros_invalidos`."
                ),
            ),
        },
    )
    def get(self, request):
        # Só contrato: a lógica (PrevisaoService) vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)
