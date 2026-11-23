"""Erros da avaliação (Avaliação N4 4a).

A `AvaliacaoView` traduz cada um para um 422 do contrato:
- `AvaliacaoIndisponivelError` -> `janela_avaliacao_fechada`;
- `NotaInvalidaError` -> `nota_invalida`;
- `ComentarioMuitoLongoError` -> `comentario_muito_longo`.
"""


class AvaliacaoIndisponivelError(Exception):
    """Refeição de outro dia ou que ainda não começou (RF15.1)."""


class NotaInvalidaError(Exception):
    """Nota ausente, fora de 1 a 5 ou que não é um número inteiro."""


class ComentarioMuitoLongoError(Exception):
    """Comentário com mais de 500 caracteres."""
