"""Views do app cadastro."""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cadastro.serializers import (
    ApelidoIndisponivelSerializer,
    CadastroCriadoSerializer,
    CadastroEntradaSerializer,
    LoginEntradaSerializer,
    ReenvioConfirmacaoEntradaSerializer,
    SessaoSerializer,
)
from config.erros import ErroSerializer


class CadastroView(APIView):
    """POST /api/cadastro/ (RF01, Cadastro N4 4a). Lógica na BE-05."""

    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Cria uma conta pendente",
        tags=["cadastro"],
        request=CadastroEntradaSerializer,
        responses={
            201: CadastroCriadoSerializer,
            409: OpenApiResponse(
                ApelidoIndisponivelSerializer,
                description=(
                    "Só professor/servidor: o apelido extraído do e-mail já "
                    "existe ou é inválido. Reenviar com `apelido`."
                ),
            ),
            422: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Dados rejeitados. Matrícula/SIAPE ou e-mail já usados "
                    "dão a mesma mensagem, sem dizer qual dos dois (RI01)."
                ),
            ),
        },
    )
    def post(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class ConfirmacaoEmailView(APIView):
    """POST /api/confirmar-email/{token}/ (RF02.1, Cadastro N4 4b)."""

    # Público: quem confirma ainda não tem login.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Confirma o e-mail pelo link recebido",
        tags=["cadastro"],
        # O token vem na URL, sem corpo na requisição.
        request=None,
        parameters=[
            OpenApiParameter(
                "token",
                str,
                OpenApiParameter.PATH,
                description="Token do link enviado por e-mail (uso único, 24 h).",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="E-mail confirmado: a conta passa a poder entrar (RF03).",
            ),
            410: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Link expirado, inválido ou já usado (RF02.1). "
                    "`codigo`: `token_invalido_ou_expirado`. "
                    "O front oferece reenviar o link."
                ),
            ),
        },
    )
    def post(self, request, token):
        # Só contrato: a lógica (ConfirmacaoEmailService) vem na BE-05.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class ReenvioConfirmacaoView(APIView):
    """POST /api/reenviar-confirmacao/ (RF02.2, Cadastro N4 4b)."""

    # Público: quem pede o reenvio ainda não consegue entrar.
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Pede um novo link de confirmação de e-mail",
        tags=["cadastro"],
        request=ReenvioConfirmacaoEntradaSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    "Pedido recebido. A resposta é a mesma exista ou não uma "
                    "conta pendente, para não revelar quais contas existem. "
                    "Quando há conta pendente, o novo link vale 24 h (RF02.2)."
                ),
            ),
            422: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Não veio `matriculaSiape` nem `token`. "
                    "`codigo`: `dados_invalidos`."
                ),
            ),
        },
    )
    def post(self, request):
        # Só contrato: a lógica (ConfirmacaoEmailService) vem na BE-05.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class SessaoView(APIView):
    """/api/sessao/ (Cadastro N4 4c): POST entra, GET diz quem sou, DELETE sai.

    Uma rota, três verbos. O padrão do projeto é fechado (IsAuthenticated),
    então só o POST (login) é liberado: quem entra ainda não tem sessão.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return super().get_permissions()

    @extend_schema(
        summary="Entra na conta (login)",
        description=(
            "Matrícula (9 dígitos) ou SIAPE (7 dígitos) no mesmo campo. "
            "O servidor grava o cookie de sessão (HttpOnly) e o `csrftoken`. "
            "Um 401 aqui é senha ou matrícula errada, não sessão expirada: "
            "a tela de login mostra a mensagem do erro (o `authStore` já "
            "está vazio, então limpá-lo de novo não causa problema)."
        ),
        tags=["cadastro"],
        request=LoginEntradaSerializer,
        responses={
            200: SessaoSerializer,
            401: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Credenciais inválidas, com mensagem genérica (RF03.1). "
                    "Vale também para conta suspensa ou removida. "
                    "`codigo`: `credenciais_invalidas`."
                ),
            ),
            403: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Credenciais corretas, mas o e-mail ainda não foi "
                    "confirmado (RF02.2). `codigo`: `conta_nao_confirmada`. "
                    "O front oferece reenviar o link."
                ),
            ),
            429: OpenApiResponse(
                ErroSerializer,
                description=(
                    "5 tentativas malsucedidas em 10 minutos: bloqueado por "
                    "10 minutos (RF03.2). `codigo`: `login_bloqueado`."
                ),
            ),
        },
    )
    def post(self, request):
        # Só contrato: a lógica (LoginService) vem na BE-05.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    @extend_schema(
        summary="Quem sou eu (sessão atual)",
        description=(
            "Devolve só apelido, tipo e avisoPrivacidadePendente, nunca "
            "matrícula/SIAPE ou e-mail (RI10)."
        ),
        tags=["cadastro"],
        responses={
            200: SessaoSerializer,
            401: OpenApiResponse(
                ErroSerializer,
                description="Sem sessão. `codigo`: `nao_autenticado`.",
            ),
        },
    )
    def get(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    @extend_schema(
        summary="Sai da conta (logout)",
        tags=["cadastro"],
        responses={
            204: OpenApiResponse(description="Sessão atual encerrada (RF03.3)."),
            401: OpenApiResponse(
                ErroSerializer,
                description="Sem sessão. `codigo`: `nao_autenticado`.",
            ),
        },
    )
    def delete(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class AceiteAvisoPrivacidadeView(APIView):
    """POST /api/privacidade/aceite/ (RF11, Cadastro N4 4d).

    Sem permission_classes de propósito: o padrão do projeto já exige login.
    """

    @extend_schema(
        summary="Registra a ciência do aviso de privacidade",
        description=(
            "Sem corpo. O servidor grava a versão atual do aviso e a hora do "
            "servidor (RF11, RNF07.1)."
        ),
        tags=["cadastro"],
        request=None,
        responses={
            204: OpenApiResponse(description="Ciência registrada."),
            401: OpenApiResponse(
                ErroSerializer,
                description="Sem sessão. `codigo`: `nao_autenticado`.",
            ),
        },
    )
    def post(self, request):
        # Só contrato: a lógica (AvisoPrivacidadeService) vem na BE-05.
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)
