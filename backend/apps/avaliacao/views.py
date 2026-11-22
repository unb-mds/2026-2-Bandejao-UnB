"""Views do app avaliacao (BE-13, RF15, Avaliação N4 4a e 4b)."""

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.avaliacao.avaliacao_publica_mapper import AvaliacaoPublicaMapper
from apps.avaliacao.avaliacao_repository import AvaliacaoRepository
from apps.avaliacao.avaliacao_service import AvaliacaoService
from apps.avaliacao.erros import (
    AvaliacaoIndisponivelError,
    ComentarioMuitoLongoError,
    NotaInvalidaError,
)
from apps.avaliacao.serializers import (
    AvaliacaoEntradaSerializer,
    AvaliacaoRegistradaSerializer,
    AvaliacoesDaRefeicaoSerializer,
    ResumoRefeicaoSerializer,
)
from apps.cardapio.horario_refeicao_resolver import intervalo
from apps.cardapio.models import Refeicao, TipoRefeicao
from apps.cardapio.parametros_consulta import (
    ParametrosInvalidos,
    buscar_campus,
    ler_data,
    ler_id_do_campus,
)
from config.erros import ErroSerializer

# Os únicos parâmetros do resumo, como no cardápio: um nome errado daria 200
# com o padrão no lugar do valor pedido.
PARAMETROS_DO_RESUMO = ("campus", "data")


def erro(codigo, mensagem, situacao):
    return Response({"codigo": codigo, "mensagem": mensagem}, status=situacao)


def buscar_refeicao(refeicao_id):
    """404 `refeicao_nao_encontrada`. Um id grande demais para o pk também
    não acha nada (o Django não chega a consultar)."""
    refeicao = Refeicao.objects.select_related("campus").filter(pk=refeicao_id).first()
    if refeicao is None:
        raise NotFound(
            "Esta refeição não está no cardápio.", code="refeicao_nao_encontrada"
        )
    return refeicao


def ler_corpo(dados):
    """`(refeicaoId, nota, comentario)`, ou None se o corpo está fora do formato.

    A nota segue como veio: ausente ou inválida é o 422 `nota_invalida` do
    contrato, conferido pelo `NotaValidator`. Já `refeicaoId` que não é
    inteiro e comentário que não é texto são erro do cliente (400).
    """
    if not isinstance(dados, dict):
        return None
    refeicao_id = dados.get("refeicaoId")
    comentario = dados.get("comentario")
    if isinstance(refeicao_id, bool) or not isinstance(refeicao_id, int):
        return None
    if comentario is not None and not isinstance(comentario, str):
        return None
    return refeicao_id, dados.get("nota"), comentario


def mensagem_janela_fechada(refeicao, agora):
    """Ex.: "A avaliação do almoço abre às 11h00, quando a refeição começa."."""
    if refeicao.data != timezone.localdate(agora):
        return "Só dá para avaliar as refeições de hoje, até 23h59."
    nome = TipoRefeicao(refeicao.tipo).label.lower()
    # O mesmo início do Anexo A que o JanelaAvaliacaoValidator confere.
    inicio, _ = intervalo(refeicao.tipo)
    return f"A avaliação do {nome} abre às {inicio:%Hh%M}, quando a refeição começa."


def conferir_nomes_do_resumo(query):
    desconhecidos = [nome for nome in query if nome not in PARAMETROS_DO_RESUMO]
    if desconhecidos:
        raise ParametrosInvalidos(
            f"Parâmetro desconhecido: {', '.join(desconhecidos)}."
        )
    repetidos = [nome for nome in PARAMETROS_DO_RESUMO if len(query.getlist(nome)) > 1]
    if repetidos:
        raise ParametrosInvalidos(
            f"Parâmetro enviado mais de uma vez: {', '.join(repetidos)}."
        )


class AvaliacaoView(APIView):
    """POST /api/avaliacoes/ (RF15, Avaliação N4 4a).

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
            400: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Corpo fora do formato: `refeicaoId` ausente ou que não "
                    "seja inteiro, ou `comentario` que não seja texto. "
                    "`codigo`: `dados_invalidos`."
                ),
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
        corpo = ler_corpo(request.data)
        if corpo is None:
            return erro(
                "dados_invalidos",
                "Dados da avaliação inválidos.",
                status.HTTP_400_BAD_REQUEST,
            )
        refeicao_id, nota, comentario = corpo
        refeicao = buscar_refeicao(refeicao_id)
        agora = timezone.now()
        try:
            registrada = AvaliacaoService().avaliar(
                request.user, refeicao, nota, comentario, agora
            )
        except AvaliacaoIndisponivelError:
            return erro(
                "janela_avaliacao_fechada",
                mensagem_janela_fechada(refeicao, agora),
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except NotaInvalidaError:
            return erro(
                "nota_invalida",
                "Escolha uma nota de 1 a 5 estrelas.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ComentarioMuitoLongoError:
            return erro(
                "comentario_muito_longo",
                "O comentário pode ter no máximo 500 caracteres.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        avaliacao = registrada.avaliacao
        pontos = registrada.pontos
        saida = AvaliacaoRegistradaSerializer(
            {
                "avaliacao": {
                    "id": avaliacao.id,
                    "refeicaoId": avaliacao.refeicao_id,
                    "nota": avaliacao.nota,
                    "comentario": avaliacao.comentario or "",
                    "criadaEm": avaliacao.criada_em,
                    "editadaEm": avaliacao.editada_em,
                },
                "pontos": {
                    "total": pontos.total,
                    "contribuicao": pontos.contribuicao,
                    "avaliacaoLiberada": pontos.avaliacao_liberada,
                },
            }
        )
        situacao = status.HTTP_201_CREATED if registrada.criada else status.HTTP_200_OK
        return Response(saida.data, status=situacao)


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
        refeicao = buscar_refeicao(refeicaoId)
        repositorio = AvaliacaoRepository()
        resumo = repositorio.media_e_quantidade(refeicao)
        comentarios = AvaliacaoPublicaMapper().para_publico(
            repositorio.listar_por_refeicao(refeicao)
        )
        saida = AvaliacoesDaRefeicaoSerializer(
            {
                "resumoAvaliacoes": {
                    "media": resumo.media,
                    "quantidade": resumo.quantidade,
                },
                "comentarios": [
                    {
                        "apelido": publica.apelido,
                        "nota": publica.nota,
                        "comentario": publica.comentario,
                        "criadaEm": publica.criada_em,
                    }
                    for publica in comentarios
                ],
            }
        )
        return Response(saida.data)


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
        query = request.query_params
        # Todos os 400 antes do 404 do campus, como no cardápio (#217).
        conferir_nomes_do_resumo(query)
        campus_id = ler_id_do_campus(query.get("campus"))
        data = ler_data(query.get("data"), "data") or timezone.localdate()
        campus = buscar_campus(campus_id)
        resumos = AvaliacaoRepository().resumos_do_dia(campus, data)
        saida = ResumoRefeicaoSerializer(
            [
                {
                    "refeicaoId": resumo.refeicao_id,
                    "tipo": resumo.tipo,
                    "media": resumo.media,
                    "quantidade": resumo.quantidade,
                }
                for resumo in resumos
            ],
            many=True,
        )
        return Response(saida.data)
