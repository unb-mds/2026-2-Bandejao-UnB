"""AvaliacaoPublicaMapper: como uma avaliação aparece para terceiros (N4 4b).

É o único lugar por onde uma conta fica visível a outras pessoas, e só sai o
apelido: nunca matrícula/SIAPE nem e-mail (RI10, ADR 0008). Sem o campo
`distintivo` do N4: a Bandeja de Ouro está fora (backlog, seção de escopo).
"""

from dataclasses import dataclass
from datetime import datetime

from apps.avaliacao.models import Avaliacao

USUARIO_REMOVIDO = "usuário removido"


@dataclass(frozen=True)
class AvaliacaoPublica:
    apelido: str
    nota: int
    comentario: str
    criada_em: datetime


class AvaliacaoPublicaMapper:
    def para_publico(self, avaliacoes: list[Avaliacao]) -> list[AvaliacaoPublica]:
        """Converte na ordem recebida.

        Conta apagada (RNF07.4): o vínculo vira nulo (`SET_NULL`) e o autor
        aparece como "usuário removido", sem a avaliação sumir.
        """
        return [
            AvaliacaoPublica(
                apelido=(
                    USUARIO_REMOVIDO
                    if avaliacao.usuario_id is None
                    else avaliacao.usuario.apelido
                ),
                nota=avaliacao.nota,
                comentario=avaliacao.comentario or "",
                criada_em=avaliacao.criada_em,
            )
            for avaliacao in avaliacoes
        ]
