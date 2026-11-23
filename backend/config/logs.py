"""Filtros de log do projeto (#120)."""

import logging
import re

# O token do link de confirmação vai no path (`/api/confirmar-email/{token}/`).
# Barras repetidas e maiúsculas também contam: o Django responde 404, mas a
# linha do log é gravada do mesmo jeito.
TOKEN_NO_PATH = re.compile(r"(/+api/+confirmar-email/+)[^/\s]+", re.IGNORECASE)


class MascaraTokenDoPath(logging.Filter):
    """Troca o token do path por `***` antes de o registro ser gravado.

    Quem lê o log do servidor não pode confirmar a conta de outra pessoa
    enquanto o link vale (24 h). Fica no logger `django.request`, que grava
    o path de todo 5xx, e nos loggers do Gunicorn em produção
    (`config/log_gunicorn.py`): o de acesso e o de erros.
    """

    def filter(self, record):
        mensagem = record.getMessage()
        mascarada = TOKEN_NO_PATH.sub(r"\1***", mensagem)
        if mascarada != mensagem:
            record.msg = mascarada
            record.args = None
        return True
