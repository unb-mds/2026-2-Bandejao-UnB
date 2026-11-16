"""Views do app cardapio."""

import hashlib
import json

from django.utils.cache import (
    get_conditional_response,
    patch_cache_control,
    quote_etag,
)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cardapio.localizacao_campus_config import LocalizacaoCampusConfig
from apps.cardapio.serializers import (
    CampusPublicoSerializer,
    CardapioFiltradoSerializer,
)
from config.erros import ErroSerializer


class CampiView(APIView):
    """GET /api/campi/ (Exposição N4 4b)."""

    # Público: o PWA lê a lista antes de qualquer login.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Lista os campi",
        description=(
            "Só `id` e `nome`, em ordem de `id`. O raio do RU nunca é "
            "publicado. A resposta leva um `ETag` e "
            "`Cache-Control: private, no-cache`: o navegador guarda a lista e "
            "manda o `ETag` de volta em `If-None-Match`. Se a lista não mudou, "
            "a resposta é 304, sem corpo."
        ),
        tags=["cardapio"],
        parameters=[
            OpenApiParameter(
                "If-None-Match",
                str,
                OpenApiParameter.HEADER,
                description="`ETag` de uma resposta anterior. O navegador manda sozinho.",
            ),
            OpenApiParameter(
                "ETag",
                str,
                OpenApiParameter.HEADER,
                response=[200, 304],
                description="Muda só quando um `id` ou um `nome` da lista muda.",
            ),
            OpenApiParameter(
                "Cache-Control",
                str,
                OpenApiParameter.HEADER,
                response=[200, 304],
                description="Sempre `private, no-cache`.",
            ),
        ],
        responses={
            200: CampusPublicoSerializer(many=True),
            304: OpenApiResponse(
                description="Lista igual à do `If-None-Match`. Sem corpo.",
            ),
        },
    )
    def get(self, request):
        # O serializer é a lista positiva do que sai: só id e nome.
        dados = CampusPublicoSerializer(LocalizacaoCampusConfig.campi(), many=True).data
        # JSON canônico: o mesmo conteúdo dá sempre o mesmo hash, em qualquer
        # worker (não usar hash() do Python, que muda a cada processo).
        corpo = json.dumps(
            dados, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        etag = quote_etag(hashlib.sha256(corpo.encode()).hexdigest())

        resposta = Response(dados)
        resposta["ETag"] = etag
        # private: quem está logado recebe o Set-Cookie da sessão junto
        # (SESSION_SAVE_EVERY_REQUEST), que um cache compartilhado não pode
        # guardar. no-cache: o navegador guarda, mas confere a cada uso.
        patch_cache_control(resposta, private=True, no_cache=True)
        # Os cabeçalhos vêm antes: o 304 copia o ETag e o Cache-Control daqui.
        return get_conditional_response(request, etag=etag, response=resposta)


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
