"""Tratador de exceções do DRF no formato de erro do projeto (BE-03, 3.4, #112)."""

from django.http import Http404, JsonResponse
from django.views import defaults
from rest_framework.exceptions import APIException, NotFound
from rest_framework.views import exception_handler

# Código padrão do DRF (ou da exceção do projeto) -> (codigo, mensagem).
TRADUCOES = {
    "not_authenticated": (
        "nao_autenticado",
        "É preciso entrar na conta para continuar.",
    ),
    # Mensagem genérica de propósito: não diz se errou a matrícula ou a senha.
    "authentication_failed": (
        "credenciais_invalidas",
        "Matrícula/SIAPE ou senha incorretas.",
    ),
    # Corpo ilegível: chega antes do serializer, então a view não traduz.
    "parse_error": (
        "json_invalido",
        "O corpo do pedido não é um JSON válido.",
    ),
    "unsupported_media_type": (
        "tipo_de_conteudo_invalido",
        "Envie o corpo em JSON (Content-Type: application/json).",
    ),
    "not_found": (
        "nao_encontrado",
        "O recurso pedido não existe.",
    ),
    "method_not_allowed": (
        "metodo_nao_permitido",
        "Esta rota não aceita esse método.",
    ),
    "csrf_invalido": (
        "csrf_invalido",
        (
            "Não foi possível confirmar a origem do pedido. "
            "Recarregue a página e tente de novo."
        ),
    ),
}


def tratador_de_excecoes(exc, context):
    """Converte erros de mensagem única para `{"codigo", "mensagem"}`.

    - Códigos de TRADUCOES (sem sessão, credenciais, CSRF, corpo ilegível,
      404 e 405) usam o texto de lá.
    - Exceção levantada com código próprio usa esse código e a mensagem dela:
      `raise PermissionDenied("Confirme seu e-mail.", code="conta_nao_confirmada")`.
    - O resto (validação, 403 sem código próprio) segue como o DRF devolve.
      O 422 de validação de cada rota fica com a view (BE-05 e seguintes).
    """
    if isinstance(exc, Http404):
        # Do `get_object_or_404`. O DRF faz a mesma troca, mas só por dentro.
        exc = NotFound()
    resposta = exception_handler(exc, context)
    if resposta is None or not isinstance(exc, APIException):
        return resposta
    codigo = exc.get_codes()
    if not isinstance(codigo, str):
        return resposta
    if codigo in TRADUCOES:
        codigo, mensagem = TRADUCOES[codigo]
    elif codigo != exc.default_code:
        mensagem = str(exc.detail)
    else:
        return resposta
    resposta.data = {"codigo": codigo, "mensagem": mensagem}
    return resposta


ERRO_INTERNO = (
    "erro_interno",
    "Algo deu errado no servidor. Tente de novo em alguns minutos.",
)


def _e_da_api(request):
    return request.path.startswith("/api/")


def erro_404(request, exception):
    """`handler404`: rota inexistente em `/api/` também sai em JSON (#121).

    O 404 de uma rota que existe passa pelo tratador acima; este é o de quando
    nenhuma rota casa, que o Django responde antes do DRF. Fora de `/api/`
    (admin), fica a página padrão. Com DEBUG=True o Django mostra a página de
    depuração no lugar deste handler.
    """
    if not _e_da_api(request):
        return defaults.page_not_found(request, exception)
    codigo, mensagem = TRADUCOES["not_found"]
    return JsonResponse({"codigo": codigo, "mensagem": mensagem}, status=404)


def erro_500(request):
    """`handler500`: erro inesperado em `/api/` sai em JSON, sem o traceback.

    O traceback continua indo para o log (`django.request`, no settings.py).
    """
    if not _e_da_api(request):
        return defaults.server_error(request)
    codigo, mensagem = ERRO_INTERNO
    return JsonResponse({"codigo": codigo, "mensagem": mensagem}, status=500)
