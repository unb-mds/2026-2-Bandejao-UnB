"""Views do app gamificacao (entram nas histórias de usuário)."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.gamificacao.serializers import (
    ProgressoSerializer,
    RankingPublicoSerializer,
)
from config.erros import ErroSerializer

ERRO_401 = OpenApiResponse(
    ErroSerializer,
    description="Sem sessão. `codigo`: `nao_autenticado`.",
)


class ProgressoView(APIView):
    """GET /api/gamificacao/progresso/ (RF26, Gamificação N4 4c).

    Sem permission_classes de propósito: o padrão do projeto já exige login.
    """

    @extend_schema(
        summary="Meu progresso: patente, pontos e sequência",
        description="Só a própria pessoa vê. Nunca traz a posição de ninguém.",
        tags=["gamificacao"],
        responses={200: ProgressoSerializer, 401: ERRO_401},
    )
    def get(self, request):
        # Só contrato: a lógica (ProgressoService) vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class RankingAdesaoView(APIView):
    """POST e DELETE /api/gamificacao/adesao/ (RF27.1).

    Sem permission_classes de propósito: o padrão do projeto já exige login.
    """

    @extend_schema(
        summary="Entra no ranking do semestre",
        description="A adesão é desligada por padrão (RF27.1).",
        tags=["gamificacao"],
        request=None,
        responses={204: None, 401: ERRO_401},
    )
    def post(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    @extend_schema(
        summary="Sai do ranking do semestre",
        description=(
            "Tira a conta do ranking na hora. Os pontos continuam "
            "acumulando. O PWA deve buscar o ranking de novo."
        ),
        tags=["gamificacao"],
        responses={204: None, 401: ERRO_401},
    )
    def delete(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class RankingView(APIView):
    """GET /api/ranking/{campusId}/ (RF27, Gamificação N4 4c)."""

    # Público: só posição, apelido e patente (RI10, RI12).
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Ranking do semestre corrente de um campus",
        description=(
            "Só quem aderiu aparece. Cada linha traz posição, apelido e "
            "patente: nunca pontos, matrícula/SIAPE nem e-mail (RI10)."
        ),
        tags=["gamificacao"],
        parameters=[
            OpenApiParameter(
                "campusId",
                int,
                OpenApiParameter.PATH,
                description="Id do campus (o de GET /api/campi/).",
            ),
        ],
        responses={
            200: RankingPublicoSerializer,
            404: OpenApiResponse(
                ErroSerializer,
                description="Campus inexistente. `codigo`: `campus_nao_encontrado`.",
            ),
        },
    )
    def get(self, request, campusId):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)
