"""Views do app cardapio."""

import hashlib
import logging
import re
from datetime import date

from django.http import HttpResponse, HttpResponseNotModified
from django.utils import timezone
from django.utils.cache import parse_etags, patch_cache_control, quote_etag
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cardapio.cardapio_query_service import CardapioQueryService
from apps.cardapio.dieta_selecionada import DietaSelecionada
from apps.cardapio.localizacao_campus_config import LocalizacaoCampusConfig
from apps.cardapio.models import Campus, Marcador, TipoRefeicao
from apps.cardapio.semana_cardapio_resolver import DURACAO_SEMANA
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


# Só dígitos ASCII: `int()` aceitaria " 1", "+1" e dígitos de outras escritas.
SO_DIGITOS = re.compile(r"[0-9]+")
# AAAA-MM-DD: `date.fromisoformat` aceitaria também "20261123".
FORMATO_DATA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# Faixa aceita em `semana` e `dia`. Longe dos extremos do `date` (anos 1 e
# 9999), onde somar ou subtrair a semana daria OverflowError (500).
DATA_MINIMA = date(2000, 1, 1)
DATA_MAXIMA = date(2099, 12, 31)
# Os únicos parâmetros do contrato. Um nome errado (`marcador`, o
# `marcadores[]` do axios) daria 200 sem filtro nenhum, como se fosse seguro.
PARAMETROS = ("campus", "semana", "dia", "refeicao", "marcadores", "dieta")


class ParametrosInvalidos(ParseError):
    """400 `parametros_invalidos` no formato `{codigo, mensagem}`.

    O `tratador_de_excecoes` (config/excecoes.py) usa o `code` e a mensagem
    da exceção. Não é o `ValidationError` do DRF de propósito: o detalhe dele
    é uma lista, e o tratador o deixaria no formato padrão de validação. O
    `code` é obrigatório: sem ele, o `ParseError` sairia como `json_invalido`.
    """

    def __init__(self, mensagem):
        super().__init__(mensagem, code="parametros_invalidos")


def _ler_campus(valor):
    if valor is None:
        raise ParametrosInvalidos("Informe o campus.")
    if not SO_DIGITOS.fullmatch(valor):
        raise ParametrosInvalidos("O campus deve ser o id numérico de GET /api/campi/.")
    campus = Campus.objects.filter(pk=int(valor)).first()
    if campus is None:
        raise ParametrosInvalidos("Não existe campus com esse id.")
    return campus


def _ler_data(valor, nome):
    if valor is None:
        return None
    try:
        if not FORMATO_DATA.fullmatch(valor):
            raise ValueError
        data = date.fromisoformat(valor)
    except ValueError:
        raise ParametrosInvalidos(
            f"O parâmetro {nome} deve ser uma data válida no formato AAAA-MM-DD."
        ) from None
    if not DATA_MINIMA <= data <= DATA_MAXIMA:
        raise ParametrosInvalidos(
            f"O parâmetro {nome} deve ser uma data entre "
            f"{DATA_MINIMA.isoformat()} e {DATA_MAXIMA.isoformat()}."
        )
    return data


def _ler_opcao(valor, opcoes, mensagem):
    if valor is not None and valor not in opcoes.values:
        raise ParametrosInvalidos(mensagem)
    return valor


def _ler_marcadores(valor):
    """Lê os nomes da tabela MARCADOR separados por vírgula.

    Devolve cada nome uma vez. Espaços em volta e nomes repetidos são aceitos; item vazio e nome
    desconhecido dão 400 (decisão de 21/11/2026: um alergênico escrito errado
    não pode ser ignorado em silêncio).
    """
    if valor is None or not valor.strip():
        return []
    nomes = [nome.strip() for nome in valor.split(",")]
    if "" in nomes:
        raise ParametrosInvalidos("A lista de marcadores tem um item vazio.")
    nomes = list(dict.fromkeys(nomes))
    conhecidos = set(
        Marcador.objects.filter(nome__in=nomes).values_list("nome", flat=True)
    )
    desconhecidos = [nome for nome in nomes if nome not in conhecidos]
    if len(desconhecidos) == 1:
        raise ParametrosInvalidos(f"Marcador desconhecido: {desconhecidos[0]}.")
    if desconhecidos:
        raise ParametrosInvalidos(
            f"Marcadores desconhecidos: {', '.join(desconhecidos)}."
        )
    return nomes


def _conferir_nomes(query):
    """Só os parâmetros do contrato, cada um uma vez.

    O `QueryDict.get` fica com o último valor de um parâmetro repetido: com
    `marcadores=ovo&marcadores=soja`, o `ovo` sumiria sem aviso.
    """
    desconhecidos = [nome for nome in query if nome not in PARAMETROS]
    if len(desconhecidos) == 1:
        raise ParametrosInvalidos(f"Parâmetro desconhecido: {desconhecidos[0]}.")
    if desconhecidos:
        raise ParametrosInvalidos(
            f"Parâmetros desconhecidos: {', '.join(desconhecidos)}."
        )
    repetidos = [nome for nome in PARAMETROS if len(query.getlist(nome)) > 1]
    if repetidos:
        raise ParametrosInvalidos(
            f"Parâmetro enviado mais de uma vez: {', '.join(repetidos)}. "
            "Para vários marcadores, use um só, separado por vírgulas."
        )


def _ler_parametros(query):
    """Valida a query string inteira antes de consultar o cardápio."""
    _conferir_nomes(query)
    campus = _ler_campus(query.get("campus"))
    semana = _ler_data(query.get("semana"), "semana")
    dia = _ler_data(query.get("dia"), "dia")
    if semana and dia and not semana <= dia <= semana + DURACAO_SEMANA:
        raise ParametrosInvalidos("O dia pedido não pertence à semana pedida.")
    refeicao = _ler_opcao(
        query.get("refeicao"),
        TipoRefeicao,
        "A refeição deve ser cafe, almoco ou jantar.",
    )
    dieta = _ler_opcao(
        query.get("dieta"),
        DietaSelecionada,
        "A dieta deve ser sem_filtro, ovolactovegetariano ou vegetariano_estrito.",
    )
    return {
        "campus": campus,
        "semana": semana,
        "dia": dia,
        "refeicao": refeicao,
        "marcadores_selecionados": _ler_marcadores(query.get("marcadores")),
        "dieta": DietaSelecionada(dieta or DietaSelecionada.SEM_FILTRO),
    }


def _para_o_contrato(cardapio):
    """CardapioFiltrado -> nomes do contrato (camelCase do serializer)."""
    return {
        "campus": cardapio.campus.pk,
        "refeicao": cardapio.refeicao,
        "data": cardapio.data,
        "refeicaoEncerrada": cardapio.refeicao_encerrada,
        "status": cardapio.status,
        "avisoSujeitoAAlteracao": cardapio.aviso_sujeito_a_alteracao,
        "alergenosIndisponivel": cardapio.alergenos_indisponivel,
        "filtroMarcadorDesativado": cardapio.filtro_marcador_desativado,
        "categorias": [
            {
                "nome": categoria.nome,
                "semOpcaoCompativel": categoria.sem_opcao_compativel,
                "pratos": [
                    {
                        "descricao": prato.descricao,
                        "marcadores": prato.marcadores,
                        "contemMarcadorSelecionado": (
                            prato.contem_marcador_selecionado
                        ),
                    }
                    for prato in categoria.pratos
                ],
            }
            for categoria in cardapio.categorias
        ],
    }


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
                description=(
                    "Semana a exibir, pela data do primeiro dia (AAAA-MM-DD, "
                    "entre 2000-01-01 e 2099-12-31). Serve só para escolher o "
                    "dia quando `dia` é omitido; se a semana está publicada, "
                    "quem diz é a data do PDF lido do campus. Omitida: semana "
                    "vigente."
                ),
            ),
            OpenApiParameter(
                "dia",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                description=(
                    "Dia a exibir (AAAA-MM-DD, dentro da `semana`, se ela "
                    "vier). Omitido: o dia corrente ou, se a `semana` pedida "
                    "não contém hoje, o primeiro dia dela. Sem `refeicao`, um "
                    "dia sem serviço passa ao próximo dia com serviço (RN05), "
                    "e `data` na resposta diz qual."
                ),
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
                description=(
                    "Marcadores selecionados, num parâmetro só, separados por "
                    "vírgula (ex.: `ovo,soja`), com os nomes de "
                    "`MARCADOR`. Nome desconhecido ou item vazio dão 400."
                ),
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
                    "Parâmetro ausente ou inválido, como `campus`; parâmetro "
                    "fora da lista acima ou repetido; data fora da faixa ou "
                    "`dia` fora da `semana`. `codigo`: `parametros_invalidos`."
                ),
            ),
        },
    )
    def get(self, request):
        parametros = _ler_parametros(request.query_params)
        # O relógio é lido aqui, uma vez só, e passado adiante: assim os
        # testes simulam qualquer horário e nenhuma parte do cálculo vê um
        # instante diferente da outra.
        agora = timezone.localtime()
        cardapio = CardapioQueryService().obter_cardapio(**parametros, agora=agora)
        return Response(CardapioFiltradoSerializer(_para_o_contrato(cardapio)).data)
