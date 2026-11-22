"""ComentarioValidator: comentário opcional de até 500 caracteres (RF15.1)."""

from apps.avaliacao.erros import ComentarioMuitoLongoError


class ComentarioValidator:
    MAX_CARACTERES = 500

    def validar(self, comentario: str | None) -> str | None:
        """Devolve o comentário sem os espaços das pontas, ou None se vazio.

        O limite conta caracteres, não bytes ("ç" e emoji contam um), como o
        `CHAR_LENGTH` da constraint no MySQL. Os espaços das pontas não
        contam: saem antes da conferência.
        """
        if comentario is None:
            return None
        texto = comentario.strip()
        if len(texto) > self.MAX_CARACTERES:
            raise ComentarioMuitoLongoError
        return texto or None
