"""Views do app fila (entram nas histórias de usuário)."""

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cardapio.models import TipoRefeicao
from apps.cardapio.parametros_consulta import (
    ParametrosInvalidos,
    buscar_campus,
    ler_data,
    ler_id_do_campus,
)
from apps.fila.checkin_service import CheckinService
from apps.fila.distancia_geografica import Coordenadas
from apps.fila.erros import (
    AvisoPrivacidadePendenteError,
    CheckinForaDoHorarioError,
    CheckinRecusadoError,
)
from apps.fila.previsao_service import PrevisaoService
from apps.fila.serializers import (
    CheckinEntradaSerializer,
    CheckinRegistradoSerializer,
    PrevisaoPicoSerializer,
)
from config.erros import ErroSerializer

MENSAGENS_RECUSA = {
    "checkin_duplicado": "Você já fez o check-in desta refeição.",
    "localizacao_nao_confirmada": (
        "Não foi possível confirmar que você está no RU. "
        "Chegue mais perto e tente de novo."
    ),
}


# Os únicos parâmetros da previsão, como no cardápio e no resumo das
# avaliações: um nome errado (`dia` no lugar de `data`) daria 200 com o dia
# de hoje, como se fosse o pedido.
PARAMETROS_DA_PREVISAO = ("campus", "refeicao", "data")


def erro(codigo, mensagem, situacao):
    return Response({"codigo": codigo, "mensagem": mensagem}, status=situacao)


def mensagem_fora_do_horario(tipo_refeicao, recusa: CheckinForaDoHorarioError):
    """Ex.: "O check-in do almoço só vale das 11h00 às 14h30." (FE-05)."""
    refeicao = TipoRefeicao(tipo_refeicao).label.lower()
    return (
        f"O check-in do {refeicao} só vale das {recusa.inicio:%Hh%M} "
        f"às {recusa.fim:%Hh%M}."
    )


class CheckinView(APIView):
    """POST /api/checkins/ (RF11, RF12, Fila N4 4a).

    Sem permission_classes de propósito: o padrão do projeto já exige login.
    As coordenadas saem do corpo direto para o serviço: não vão para log,
    banco nem resposta (RI09).
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
            400: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Corpo fora do formato, campus ou refeição inexistente, ou "
                    "coordenada fora da faixa. Não conta como tentativa. "
                    "`codigo`: `dados_invalidos`."
                ),
            ),
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
        entrada = CheckinEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            # Mensagem fixa: a do DRF poderia repetir o valor enviado (RI09).
            return erro(
                "dados_invalidos",
                "Dados do check-in inválidos.",
                status.HTTP_400_BAD_REQUEST,
            )
        dados = entrada.validated_data
        tipo_refeicao = dados["tipoRefeicao"]
        try:
            registrado = CheckinService().registrar(
                request.user,
                dados["campus"],
                tipo_refeicao,
                Coordenadas(**dados["coordenadas"]),
                timezone.now(),
            )
        except AvisoPrivacidadePendenteError:
            return erro(
                "aviso_privacidade_pendente",
                "Antes do primeiro check-in, dê ciência ao aviso de privacidade.",
                status.HTTP_403_FORBIDDEN,
            )
        except CheckinForaDoHorarioError as recusa:
            return erro(
                recusa.motivo,
                mensagem_fora_do_horario(tipo_refeicao, recusa),
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except CheckinRecusadoError as recusa:
            return erro(
                recusa.motivo,
                MENSAGENS_RECUSA[recusa.motivo],
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        checkin = registrado.checkin
        pontos = registrado.pontos
        saida = CheckinRegistradoSerializer(
            {
                "checkin": {
                    "id": checkin.id,
                    "campus": checkin.campus_id,
                    "tipoRefeicao": checkin.tipo_refeicao,
                    "data": checkin.data,
                },
                "pontos": {
                    "total": pontos.total,
                    "contribuicao": pontos.contribuicao,
                    "avaliacaoLiberada": pontos.avaliacao_liberada,
                },
            }
        )
        return Response(saida.data, status=status.HTTP_201_CREATED)


def ler_parametros_da_previsao(query):
    """`(campus, refeicao, data)` da query string, ou 400/404.

    Todos os 400 vêm antes do 404 do campus, como no cardápio (#217). Sem
    `data`, vale o dia de hoje no horário de Brasília.
    """
    desconhecidos = [nome for nome in query if nome not in PARAMETROS_DA_PREVISAO]
    if desconhecidos:
        raise ParametrosInvalidos(
            f"Parâmetro desconhecido: {', '.join(desconhecidos)}."
        )
    repetidos = [
        nome for nome in PARAMETROS_DA_PREVISAO if len(query.getlist(nome)) > 1
    ]
    if repetidos:
        raise ParametrosInvalidos(
            f"Parâmetro enviado mais de uma vez: {', '.join(repetidos)}."
        )
    campus_id = ler_id_do_campus(query.get("campus"))
    refeicao = query.get("refeicao")
    if refeicao is None:
        raise ParametrosInvalidos("Informe a refeição.")
    if refeicao not in TipoRefeicao.values:
        raise ParametrosInvalidos("A refeição deve ser cafe, almoco ou jantar.")
    data = ler_data(query.get("data"), "data") or timezone.localdate()
    # Por último: depois de todos os 400.
    return buscar_campus(campus_id), refeicao, data


class PrevisaoView(APIView):
    """GET /api/fila/previsao/ (RF13, Fila N4 4c)."""

    # Público: devolve só agregados, nada de conta ou check-in individual.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Previsão de pico por faixa de horário",
        description=(
            "Calculada sob demanda a partir dos check-ins confirmados das 4 "
            "semanas anteriores, no mesmo dia da semana (o próprio dia não "
            "entra), e só deles: as respostas à pergunta de saída não mudam "
            "o nível (RF13, ADR 0010). As faixas de 15 minutos cobrem o "
            "horário da refeição, em horário de Brasília. A média de cada "
            "faixa considera só os dias com check-in, e neles a faixa vazia "
            "conta como zero. Em empate na maior média, todas essas faixas "
            "têm `ehPico` (RN06). Com poucos dados volta 200 com `status` "
            "igual a `dados_insuficientes` e `faixas` vazia, e não erro."
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
                    "Parâmetro ausente ou inválido, como `campus` ausente ou "
                    "que não seja só dígitos. Com o campus inexistente e outro "
                    "parâmetro inválido, a resposta é este 400. "
                    "`codigo`: `parametros_invalidos`."
                ),
            ),
            # Mesmo critério do GET /api/cardapio/ (#217).
            404: OpenApiResponse(
                ErroSerializer,
                description="Campus inexistente. `codigo`: `campus_nao_encontrado`.",
            ),
        },
    )
    def get(self, request):
        campus, refeicao, data = ler_parametros_da_previsao(request.query_params)
        previsao = PrevisaoService().calcular(campus, refeicao, data)
        saida = PrevisaoPicoSerializer(
            {
                "campus": previsao.campus.id,
                "tipoRefeicao": previsao.tipo_refeicao,
                "data": previsao.data,
                "status": previsao.status,
                "faixas": [
                    {
                        "inicio": faixa.inicio,
                        "fim": faixa.fim,
                        "nivel": faixa.nivel,
                        "ehPico": faixa.eh_pico,
                    }
                    for faixa in previsao.faixas
                ],
            }
        )
        return Response(saida.data)
