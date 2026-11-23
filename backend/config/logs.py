"""Filtros de log do projeto (#120)."""

import logging
import re

# O token do link de confirmação vai no path (`/api/confirmar-email/{token}/`).
TOKEN_NO_PATH = re.compile(r"(/api/confirmar-email/)[^/\s]+")


class MascaraTokenDoPath(logging.Filter):
    """Troca o token do path por `***` antes de o registro ser gravado.

    Quem lê o log do servidor não pode confirmar a conta de outra pessoa
    enquanto o link vale (24 h). Fica no logger `django.request`, que grava
    o path de todo 5xx.
    """

    def filter(self, record):
        mensagem = record.getMessage()
        mascarada = TOKEN_NO_PATH.sub(r"\1***", mensagem)
        if mascarada != mensagem:
            record.msg = mascarada
            record.args = None
        return True
