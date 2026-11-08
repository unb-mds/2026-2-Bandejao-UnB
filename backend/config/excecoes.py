"""Tratador de exceções do DRF no formato de erro do projeto (BE-03, 3.4)."""

from rest_framework.exceptions import NotAuthenticated
from rest_framework.views import exception_handler


def tratador_de_excecoes(exc, context):
    """Converte o erro de "sem sessão" para `{"codigo": "nao_autenticado"}`.

    Os demais erros padrão (400, 403, 404) seguem como o DRF os devolve.
    Convertê-los para o formato do projeto fica como pendência da BE-05.
    """
    resposta = exception_handler(exc, context)
    if resposta is not None and isinstance(exc, NotAuthenticated):
        resposta.data = {
            "codigo": "nao_autenticado",
            "mensagem": "É preciso entrar na conta para continuar.",
        }
    return resposta
