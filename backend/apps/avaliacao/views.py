"""Views do app avaliacao (entram nas histórias de usuário)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.avaliacao.serializers import (
    AvaliacaoEntradaSerializer,
    AvaliacaoRegistradaSerializer,
    AvaliacoesDaRefeicaoSerializer,
    ResumoRefeicaoSerializer,
)
from config.erros import ErroSerializer


class AvaliacaoView(APIView):
    """POST /api/avaliacoes/ (RF15, Avaliação N4 4a). Lógica em outra BE.

    Sem permission_classes de propósito: o padrão do projeto já exige login.
    """

    @extend_schema(
        summary="Avalia uma refeição (cria ou edita)",
        description=(
            "É sempre um upsert: avaliar de novo a mesma refeição edita a "
            "anterior (RF15). Os pontos não dependem da nota nem do comentário "
            "(RI11), e nenhum campo de pontos, de campus ou de refeição de "
            "pontuação vem do front (RN09)."
        ),
        tags=["avaliacao"],
        request=AvaliacaoEntradaSerializer,
        responses={
            201: OpenApiResponse(
                AvaliacaoRegistradaSerializer,
                description="Primeira avaliação desta refeição.",
            ),
            200: OpenApiResponse(
                AvaliacaoRegistradaSerializer,
                description="Avaliação anterior editada. Não pontua de novo.",
            ),
            401: OpenApiResponse(
                ErroSerializer,
                description="Sem sessão. `codigo`: `nao_autenticado`.",
            ),
            404: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Refeição inexistente. `codigo`: `refeicao_nao_encontrada`."
                ),
            ),
            422: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Regra de negócio violada. `codigo`: "
                    "`janela_avaliacao_fechada` (refeição fora do dia corrente "
                    "ou ainda não iniciada), `nota_invalida` (ausente ou fora "
                    "de 1 a 5) ou `comentario_muito_longo` (mais de 500 "
                    "caracteres)."
                ),
            ),
        },
    )
    def post(self, request):
        # Só contrato: a lógica (AvaliacaoService) vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class RefeicaoAvaliacoesView(APIView):
    """GET /api/refeicoes/{refeicaoId}/avaliacoes/ (RF15.2, Avaliação N4 4b)."""

    # Público: qualquer visitante lê a nota média e os comentários.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Nota média e comentários de uma refeição",
        description=(
            "Avaliações ocultas pela moderação não aparecem nem entram na "
            "média (RNF08). Autor com conta removida aparece como "
            "`usuário removido`. Nunca expõe dado pessoal do autor (RI10)."
        ),
        tags=["avaliacao"],
        parameters=[
            OpenApiParameter(
                "refeicaoId",
                int,
                OpenApiParameter.PATH,
                description="Id da refeição (inteiro, público de propósito).",
            ),
        ],
        responses={
            200: AvaliacoesDaRefeicaoSerializer,
            404: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Refeição inexistente. `codigo`: `refeicao_nao_encontrada`."
                ),
            ),
        },
    )
    def get(self, request, refeicaoId):
        # Só contrato: a lógica vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class ResumoDoDiaView(APIView):
    """GET /api/avaliacoes/resumo/ (RF20.3, Avaliação N4 4b)."""

    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Nota média e quantidade de cada refeição do dia",
        description=(
            "Uma chamada só para o seletor de refeições da tela do campus. "
            "Os comentários vêm à parte, por refeição."
        ),
        tags=["avaliacao"],
        parameters=[
            OpenApiParameter(
                "campus",
                int,
                OpenApiParameter.QUERY,
                required=True,
                description="Id do campus (o de GET /api/campi/).",
            ),
            OpenApiParameter(
                "data",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                description="Dia do resumo. Omitido: dia corrente.",
            ),
        ],
        responses={
            200: ResumoRefeicaoSerializer(many=True),
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
        # Só contrato: a lógica vem em outra BE.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)
