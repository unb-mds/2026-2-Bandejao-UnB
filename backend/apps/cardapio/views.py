"""Views do app cardapio."""

import hashlib
import logging

from django.http import HttpResponse, HttpResponseNotModified
from django.utils.cache import parse_etags, patch_cache_control, quote_etag
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cardapio.localizacao_campus_config import LocalizacaoCampusConfig
from apps.cardapio.serializers import (
    CampusPublicoSerializer,
    CardapioFiltradoSerializer,
)
from config.erros import ErroSerializer

logger = logging.getLogger(__name__)


def _sem_w(etag):
    """Tira o prefixo de ETag fraco, para a comparação fraca (RFC 9110)."""
    return etag.removeprefix("W/")


def _if_none_match_bate(request, etag):
    """True se o If-None-Match da requisição casa com o `etag` atual.

    Comparação fraca, como a RFC 9110 manda para o If-None-Match: `W/"x"`
    casa com `"x"`. Aceita uma lista (`"a", "b"`) e o `*`.
    """
    cabecalho = request.META.get("HTTP_IF_NONE_MATCH")
    if not cabecalho:
        return False
    etags = parse_etags(cabecalho)
    if etags == ["*"]:
        return True
    return _sem_w(etag) in {_sem_w(e) for e in etags}


class CampiView(APIView):
    """GET /api/campi/ (Exposição N4 4b)."""

    # Público: o PWA lê a lista antes de qualquer login.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Lista os campi",
        description=(
            "Só `id` e `nome`, em ordem de `id`. O raio do RU nunca é "
            "publicado. A resposta leva um `ETag` e "
            "`Cache-Control: private, no-cache`. Com um `fetch` comum, o "
            "navegador guarda a lista, manda o `If-None-Match` sozinho e "
            "entrega o corpo guardado quando nada mudou. Quem mandar o "
            "`If-None-Match` à mão (com uma cópia no `localStorage`, por "
            "exemplo) recebe o 304 sem corpo e usa a própria cópia. Só o "
            "`If-None-Match` é tratado: `If-Match`, `If-Modified-Since` e "
            "`If-Unmodified-Since` são ignorados."
        ),
        tags=["cardapio"],
        parameters=[
            OpenApiParameter(
                "If-None-Match",
                str,
                OpenApiParameter.HEADER,
                description=(
                    "Um ou mais `ETag` de respostas anteriores, ou `*`. "
                    "Comparação fraca."
                ),
            ),
            OpenApiParameter(
                "ETag",
                str,
                OpenApiParameter.HEADER,
                response=[200, 304],
                description=(
                    "SHA-256 dos bytes do corpo do 200. Muda quando a lista "
                    "publicada muda (campus incluído ou removido, `id` ou "
                    "`nome` alterado). Não muda com o raio de confirmação "
                    "nem com as coordenadas do RU."
                ),
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
                description=(
                    "Algum `ETag` do `If-None-Match` bate com o da lista "
                    "atual (ou veio `*`). Sem corpo."
                ),
            ),
        },
    )
    def get(self, request):
        # O serializer é a lista positiva do que sai: só id e nome.
        dados = CampusPublicoSerializer(LocalizacaoCampusConfig.campi(), many=True).data
        if not dados:
            # A tabela é povoada pela fixture da BD-03. Vazia quer dizer
            # deploy sem o loaddata: a resposta continua 200 [], mas fica o
            # rastro para quem for investigar o seletor de campus vazio.
            logger.warning("Tabela CAMPUS vazia: a fixture da BD-03 foi carregada?")

        # Os bytes são renderizados aqui, uma vez só, e servem para as duas
        # coisas: o hash do ETag e o corpo. Assim o ETag forte muda com
        # qualquer byte do corpo (formato, ordem das chaves, campos novos) e
        # um `Accept` com indent não gera outro corpo com o mesmo ETag.
        # sha256, e não hash() do Python, que muda a cada processo.
        corpo = JSONRenderer().render(dados)
        etag = quote_etag(hashlib.sha256(corpo).hexdigest())

        # Só o If-None-Match é tratado, à mão. O get_conditional_response do
        # Django também avalia If-Match e If-Unmodified-Since e responderia
        # 412 cru, sem corpo de erro e fora do contrato.
        if _if_none_match_bate(request, etag):
            resposta = HttpResponseNotModified()
        else:
            resposta = HttpResponse(corpo, content_type="application/json")
        resposta["ETag"] = etag
        # private: quem está logado recebe o Set-Cookie da sessão junto
        # (SESSION_SAVE_EVERY_REQUEST, ADR 0007), e um cache compartilhado
        # não deve guardar essa resposta nem repassá-la a outra pessoa.
        # no-cache: o navegador guarda, mas confere com o servidor a cada uso.
        patch_cache_control(resposta, private=True, no_cache=True)
        return resposta


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
