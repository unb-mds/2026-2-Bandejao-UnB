"""Tratador de exceções do DRF no formato de erro do projeto (BE-03, 3.4, #112)."""

from rest_framework.exceptions import APIException
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

    - Códigos de TRADUCOES (sem sessão, credenciais, CSRF, corpo ilegível)
      usam o texto de lá.
    - Exceção levantada com código próprio usa esse código e a mensagem dela:
      `raise PermissionDenied("Confirme seu e-mail.", code="conta_nao_confirmada")`.
    - O resto (validação, 404, 405) segue como o DRF devolve. O 422 de
      validação de cada rota fica com a view (BE-05 e seguintes).
    """
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
