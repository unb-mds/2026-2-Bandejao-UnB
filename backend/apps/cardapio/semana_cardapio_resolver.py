"""SemanaCardapioResolver: de qual semana publicada é o dia? (RF07.1, N4 4a).

A semana sai das datas do PDF do campus (RF07.1), guardadas na
`FonteCardapio`: uma linha por campus e semana, criada pelo Leitor só depois
de uma leitura com sucesso (ADR 0014). Decisão de 21/11/2026: sem linha, a
semana não está publicada, mesmo que haja `Refeicao` no banco (por exemplo,
cadastrada à mão pelo Admin sem a linha da semana).

Na Release 2 a BE-11 entrega só a semana vigente; a seguinte (RF18) fica
para outra tarefa.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from apps.cardapio.models import Campus, FonteCardapio

DURACAO_SEMANA = timedelta(days=6)


@dataclass(frozen=True)
class Semana:
    inicio: date
    fim: date
    vigente: bool


class SemanaCardapioResolver:
    def semanas_disponiveis(self, campus: Campus, dia: date) -> list[Semana]:
        """A semana publicada que contém `dia`, numa lista; vazia se não há.

        Contém = `semana_inicio <= dia <= semana_inicio + 6 dias`, com o
        primeiro e o último dia incluídos. O `dia` vem de fora porque o
        relógio é lido uma vez só, na view.
        """
        fonte = (
            FonteCardapio.objects.filter(
                campus=campus,
                semana_inicio__lte=dia,
                semana_inicio__gte=dia - DURACAO_SEMANA,
            )
            .order_by("-semana_inicio")
            .first()
        )
        if fonte is None:
            return []
        return [
            Semana(
                inicio=fonte.semana_inicio,
                fim=fonte.semana_inicio + DURACAO_SEMANA,
                vigente=True,
            )
        ]
