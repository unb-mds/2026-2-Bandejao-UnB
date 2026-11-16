"""Views do app cadastro."""

import math

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cadastro.autenticacao import CsrfObrigatorio
from apps.cadastro.aviso_privacidade_service import AvisoPrivacidadeService
from apps.cadastro.cadastro_service import (
    MENSAGEM_AVISO,
    MENSAGEM_DADOS,
    MENSAGEM_SENHA,
    MENSAGEM_SIAPE,
    CadastroService,
)
from apps.cadastro.confirmacao_email_service import ConfirmacaoEmailService
from apps.cadastro.erros import (
    ApelidoIndisponivelError,
    CadastroInvalidoError,
    ContaNaoConfirmadaError,
    CredenciaisInvalidasError,
    IdentificadorInvalidoError,
    LoginBloqueadoError,
    TokenExpiradoOuInvalidoError,
)
from apps.cadastro.login_service import LoginService
from apps.cadastro.models import MENSAGEM_APELIDO
from apps.cadastro.serializers import (
    ApelidoIndisponivelSerializer,
    CadastroCriadoSerializer,
    CadastroEntradaSerializer,
    LoginEntradaSerializer,
    ReenvioConfirmacaoEntradaSerializer,
    SessaoSerializer,
)
from apps.cadastro.sessoes_da_conta import SessoesDaConta
from config.erros import ErroSerializer

# Mensagem do 422 quando o corpo nem passa no serializer. O DRF devolve todos
# os campos com erro; a ordem abaixo é a prioridade escolhida pelo time para
# mostrar um só. O {"campo": [...]} do DRF, em inglês, não vai ao front.
MENSAGENS_DO_SERIALIZER = (
    ("tipoUsuario", "Escolha se você é aluno, professor ou servidor."),
    ("aceitePrivacidade", MENSAGEM_AVISO),
    ("emailInstitucional", "Informe o seu e-mail institucional da UnB."),
    ("matriculaSiape", MENSAGEM_SIAPE),
    ("senha", MENSAGEM_SENHA),
    ("apelido", MENSAGEM_APELIDO),
)

MENSAGEM_TOKEN_INVALIDO = (
    "Este link de confirmação é inválido, expirou ou já foi usado. Peça um novo link."
)
MENSAGEM_REENVIO_SEM_DADOS = "Informe a matrícula/SIAPE ou abra o link recebido."
MENSAGEM_LOGIN_SEM_DADOS = "Informe a matrícula/SIAPE e a senha."
MENSAGEM_CONTA_NAO_CONFIRMADA = (
    "Confirme seu e-mail antes de entrar. Se o link venceu, peça um novo."
)


def dados_invalidos(mensagem):
    return Response(
        {"codigo": "dados_invalidos", "mensagem": mensagem},
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


class CsrfView(APIView):
    """GET /api/csrf/: grava o cookie `csrftoken` antes do login (#112).

    As escritas públicas (cadastro, login, confirmação, reenvio) cobram o
    CSRF mesmo sem sessão. O PWA chama esta rota ao abrir e lê o cookie.
    """

    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Grava o cookie csrftoken",
        description=(
            "Sem corpo. Chame antes da primeira escrita sem sessão (cadastro, "
            "login, confirmação, reenvio) e mande o valor do cookie no "
            "cabeçalho `X-CSRFToken`. O login troca o token: leia o cookie "
            "de novo a cada escrita (ADR 0007)."
        ),
        tags=["cadastro"],
        request=None,
        responses={204: OpenApiResponse(description="Cookie `csrftoken` gravado.")},
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class CadastroView(APIView):
    """POST /api/cadastro/ (RF01, Cadastro N4 4a)."""

    permission_classes = (AllowAny, CsrfObrigatorio)

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
                    "existe ou é inválido. Reenviar com `apelido`. "
                    "`codigo`: `apelido_indisponivel`."
                ),
            ),
            422: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Dados rejeitados. A mensagem diz o que corrigir, exceto "
                    "quando o corpo vem fora do formato esperado (mensagem "
                    "genérica). Matrícula/SIAPE ou e-mail já usados dão a "
                    "mesma mensagem, sem dizer qual dos dois (RF01.5). "
                    "`codigo`: `dados_invalidos`."
                ),
            ),
        },
    )
    def post(self, request):
        entrada = CadastroEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            erros = entrada.errors
            mensagem = next(
                (texto for campo, texto in MENSAGENS_DO_SERIALIZER if campo in erros),
                MENSAGEM_DADOS,
            )
            return dados_invalidos(mensagem)

        try:
            conta = CadastroService().registrar(
                entrada.validated_data["tipoUsuario"], entrada.para_dados_cadastro()
            )
        except ApelidoIndisponivelError as erro:
            return Response(
                {
                    "codigo": "apelido_indisponivel",
                    "mensagem": erro.mensagem,
                    "apelidoSugerido": erro.apelido_sugerido,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except CadastroInvalidoError as erro:
            return dados_invalidos(erro.mensagem)
        saida = CadastroCriadoSerializer(
            {"emailInstitucional": conta.email_institucional, "status": conta.status}
        )
        return Response(saida.data, status=status.HTTP_201_CREATED)


class ConfirmacaoEmailView(APIView):
    """POST /api/confirmar-email/{token}/ (RF02.1, Cadastro N4 4b)."""

    # Público: quem confirma ainda não tem login.
    permission_classes = (AllowAny, CsrfObrigatorio)

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
        try:
            ConfirmacaoEmailService().confirmar(token)
        except TokenExpiradoOuInvalidoError:
            # Montado aqui, e não por APIException: com o código padrão, o
            # tratador de exceções devolveria {"detail": ...} (BE-06, 7.2).
            return Response(
                {
                    "codigo": "token_invalido_ou_expirado",
                    "mensagem": MENSAGEM_TOKEN_INVALIDO,
                },
                status=status.HTTP_410_GONE,
            )
        return Response(status=status.HTTP_200_OK)


class ReenvioConfirmacaoView(APIView):
    """POST /api/reenviar-confirmacao/ (RF02.2, Cadastro N4 4b)."""

    # Público: quem pede o reenvio ainda não consegue entrar.
    permission_classes = (AllowAny, CsrfObrigatorio)

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
                    "Corpo inválido: não veio `matriculaSiape` nem `token`, "
                    "ou um deles veio vazio ou com tipo errado (mesmo que o "
                    "outro esteja certo). `codigo`: `dados_invalidos`."
                ),
            ),
        },
    )
    def post(self, request):
        entrada = ReenvioConfirmacaoEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            return dados_invalidos(MENSAGEM_REENVIO_SEM_DADOS)

        servico = ConfirmacaoEmailService()
        conta = servico.conta_para_reenvio(
            matricula_siape=entrada.validated_data.get("matriculaSiape"),
            token=entrada.validated_data.get("token"),
        )
        servico.reenviar(conta)
        # Sempre a mesma resposta, exista ou não a conta (RF02.2).
        return Response(status=status.HTTP_200_OK)


class SessaoView(APIView):
    """/api/sessao/ (Cadastro N4 4c): POST entra, GET diz quem sou, DELETE sai.

    Uma rota, três verbos. O padrão do projeto é fechado (IsAuthenticated),
    então só o POST (login) é liberado: quem entra ainda não tem sessão.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            # Sem sessão, mas cobrando o CSRF: fecha o login CSRF (#112).
            return [AllowAny(), CsrfObrigatorio()]
        return super().get_permissions()

    @extend_schema(
        summary="Entra na conta (login)",
        description=(
            "Matrícula (9 dígitos) ou SIAPE (7 dígitos) no mesmo campo. "
            "O servidor grava o cookie de sessão (HttpOnly) e o `csrftoken`. "
            "Um 401 aqui é senha ou matrícula errada, não sessão expirada: "
            "a tela de login mostra a mensagem do erro (o `authStore` já "
            "está vazio, então limpá-lo de novo não causa problema). "
            "O login troca o `csrftoken`: leia o cookie de novo antes da "
            "próxima escrita."
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
            422: OpenApiResponse(
                ErroSerializer,
                description=(
                    "Corpo inválido (falta `matriculaSiape` ou `senha`, ou "
                    "um deles não é texto) ou identificador que não tem 9 "
                    "nem 7 dígitos (RN01). Não conta como tentativa. "
                    "`codigo`: `dados_invalidos`."
                ),
            ),
            429: OpenApiResponse(
                ErroSerializer,
                description=(
                    "5 tentativas malsucedidas em 10 minutos: bloqueado por "
                    "10 minutos (RF03.2). A 5ª falha já responde 429. A "
                    "mensagem diz quantos minutos faltam, e o cabeçalho "
                    "`Retry-After`, quantos segundos. `codigo`: `login_bloqueado`."
                ),
            ),
        },
    )
    def post(self, request):
        entrada = LoginEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            return dados_invalidos(MENSAGEM_LOGIN_SEM_DADOS)

        try:
            conta = LoginService().autenticar(
                entrada.validated_data["matriculaSiape"],
                entrada.validated_data["senha"],
            )
        except IdentificadorInvalidoError as erro:
            return dados_invalidos(erro.mensagem)
        except CredenciaisInvalidasError:
            # A mensagem genérica fica no TRADUCOES de config/excecoes.py, e o
            # DRF põe o cabeçalho WWW-Authenticate do 401.
            raise AuthenticationFailed from None
        except ContaNaoConfirmadaError:
            raise PermissionDenied(
                MENSAGEM_CONTA_NAO_CONFIRMADA, code="conta_nao_confirmada"
            ) from None
        except LoginBloqueadoError as erro:
            return self._bloqueado(erro.segundos_restantes)

        SessoesDaConta().abrir(request, conta)
        return Response(self._sessao(conta))

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
        return Response(self._sessao(request.user))

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
        SessoesDaConta().encerrar_atual(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _sessao(self, conta):
        """Só apelido, tipo e aviso pendente: nunca matrícula/SIAPE nem e-mail (RI10)."""
        return SessaoSerializer(
            {
                "apelido": conta.apelido,
                "tipo": conta.tipo_usuario,
                "avisoPrivacidadePendente": conta.aviso_privacidade_pendente(),
            }
        ).data

    def _bloqueado(self, segundos_restantes):
        # Montado aqui: o Throttled do DRF acrescentaria um texto em inglês.
        minutos = math.ceil(segundos_restantes / 60)
        return Response(
            {
                "codigo": "login_bloqueado",
                "mensagem": f"Muitas tentativas. Tente de novo em {minutos} min.",
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(segundos_restantes)},
        )


class AceiteAvisoPrivacidadeView(APIView):
    """POST /api/privacidade/aceite/ (RNF07.1, Cadastro N4 4d).

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
        # Hora do servidor: o corpo, se vier, é ignorado.
        AvisoPrivacidadeService().registrar_ciencia(request.user, timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
