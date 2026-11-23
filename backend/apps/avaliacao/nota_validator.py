"""NotaValidator: nota obrigatória de 1 a 5 (RF15.1)."""

from apps.avaliacao.erros import NotaInvalidaError

NOTA_MINIMA = 1
NOTA_MAXIMA = 5


class NotaValidator:
    def validar(self, nota) -> None:
        """Só inteiro de 1 a 5. Recusa `4.0`, `"4"` e `True`.

        A nota vem direto do JSON: `True` é `int` em Python e passaria na
        faixa, e um `4.5` seria gravado como 4 sem aviso.
        """
        if isinstance(nota, bool) or not isinstance(nota, int):
            raise NotaInvalidaError
        if not NOTA_MINIMA <= nota <= NOTA_MAXIMA:
            raise NotaInvalidaError
