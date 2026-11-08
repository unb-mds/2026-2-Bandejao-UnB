"""Views do app cardapio."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cardapio.serializers import (
    CampusPublicoSerializer,
    CardapioFiltradoSerializer,
)
from config.erros import ErroSerializer


class CampiView(APIView):
    """GET /api/campi/ (Exposição N4 4b). Lógica em outra BE."""

    # Público: o PWA lê a lista antes de qualquer login.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Lista os campi",
        description="Só `id` e `nome`. O raio do RU nunca é publicado.",
        tags=["cardapio"],
        responses={200: CampusPublicoSerializer(many=True)},
    )
    def get(self, request):
        # Só contrato: a lógica vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class CardapioView(APIView):
    """GET /api/cardapio/ (Exposição N4 4a). Filtros por query string (X4)."""

    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Cardápio de uma refeição, já filtrado",
        description=(
            "Os filtros de marcador e de dieta são aplicados no backend "
            "(ADR 0005). Cardápio ainda não publicado volta 200 com "
            "`status` igual a `nao_publicado` (RF18)."
        ),
        tags=["cardapio"],
        parameters=[
            OpenApiParameter(
                "campus",
                int,
                OpenApiParameter.QUERY,
                required=True,
                description="Id do campus (o de GET /api/campi/).",
            ),
            OpenApiParameter(
                "semana",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                description="Início da semana. Omitido: semana vigente.",
            ),
            OpenApiParameter(
                "dia",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                description="Dia a exibir. Omitido: dia corrente.",
            ),
            OpenApiParameter(
                "refeicao",
                str,
                OpenApiParameter.QUERY,
                enum=["cafe", "almoco", "jantar"],
                description="Omitida: refeição padrão (RN05).",
            ),
            OpenApiParameter(
                "marcadores",
                str,
                OpenApiParameter.QUERY,
                description="Marcadores selecionados, separados por vírgula.",
            ),
            OpenApiParameter(
                "dieta",
                str,
                OpenApiParameter.QUERY,
                enum=["sem_filtro", "ovolactovegetariano", "vegetariano_estrito"],
                description="Omitida: sem_filtro.",
            ),
        ],
        responses={
            200: CardapioFiltradoSerializer,
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
        # Só contrato: a lógica (CardapioQueryService) vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)
