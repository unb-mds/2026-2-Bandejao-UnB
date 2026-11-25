"""Erros da gamificação (Gamificação N4 4a).

Nenhum vira resposta de contrato: são falhas de programação de quem chama a
pontuação. Sobem como vieram, desfazem a transação de quem chamou (a
contribuição e os pontos voltam juntos, ADR 0011) e viram um 500.
"""


class OrigemContribuicaoNaoEncontradaError(Exception):
    """O `origem_id` não é de um registro sem pontos do tipo informado.

    Sem o marcador gravado, cada nova chamada com esse id pontuaria de novo:
    por isso nenhum ponto é concedido.
    """

    def __init__(self, tipo, origem_id: int):
        super().__init__(f"{tipo} {origem_id} não existe ou já foi pontuado")
        self.tipo = tipo
        self.origem_id = origem_id
