"""ComentarioValidator: comentário opcional de até 500 caracteres (RF15.1)."""

import unicodedata

from apps.avaliacao.erros import ComentarioMuitoLongoError

# Letras Hangul que não desenham nada (fillers). São categoria "Lo", então a
# conferência por categoria abaixo não as pega.
FILLERS = frozenset("\u115f\u1160\u3164\uffa0")


def _invisivel(caractere: str) -> bool:
    """Espaço, caractere de formatação ("Cf": U+200B, BOM, ZWJ...) ou filler."""
    return (
        caractere.isspace()
        or unicodedata.category(caractere) == "Cf"
        or caractere in FILLERS
    )


class ComentarioValidator:
    MAX_CARACTERES = 500

    def validar(self, comentario: str | None) -> str | None:
        """Devolve o comentário sem os espaços das pontas, ou None se vazio.

        O limite conta caracteres, não bytes ("ç" e emoji contam um), como o
        `CHAR_LENGTH` da constraint no MySQL. Os espaços das pontas não
        contam: saem antes da conferência.

        Comentário só com caracteres invisíveis também vira None: senão
        apareceria em branco na lista pública (revisão do #230). Dentro de um
        texto visível eles ficam (o ZWJ junta emojis).
        """
        if comentario is None:
            return None
        texto = comentario.strip()
        if len(texto) > self.MAX_CARACTERES:
            raise ComentarioMuitoLongoError
        if all(_invisivel(caractere) for caractere in texto):
            return None
        return texto
