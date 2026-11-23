"""PatenteResolver: a patente dos pontos totais (RF26.1, RN11, Gamificação N4
4b).

Os limiares são como os degraus de uma escada: a patente é a do degrau mais
alto que os pontos alcançam, e o que falta é a distância até o próximo
degrau (0 no último). A patente é derivada, nunca gravada: como os pontos
totais só sobem, ela não regride. Também usado pelo `RankingPublicoMapper`
(BE-17).
"""

from bisect import bisect_right

from apps.gamificacao.patente import Patente
from config.parametros import ParametrosGamificacaoConfig

PATENTES = tuple(Patente)


class PatenteResolver:
    def __init__(self, limiares: tuple[int, ...] | None = None):
        """Sem argumentos, lê os limiares da `ParametrosGamificacaoConfig`. Os
        testes passam limiares próprios, para não depender dos números de
        hoje. Exige um limiar por `Patente`, o primeiro igual a 0 e todos em
        ordem estritamente crescente (`ValueError` se não)."""
        self.limiares = tuple(
            ParametrosGamificacaoConfig.limiares_patente
            if limiares is None
            else limiares
        )
        if len(self.limiares) != len(PATENTES):
            raise ValueError(
                f"São {len(PATENTES)} patentes e {len(self.limiares)} limiares."
            )
        if self.limiares[0] != 0:
            raise ValueError("O primeiro limiar de patente tem de ser 0.")
        if any(
            anterior >= seguinte
            for anterior, seguinte in zip(self.limiares, self.limiares[1:])
        ):
            raise ValueError("Os limiares de patente têm de ser crescentes.")

    def patente(self, pontos_totais: int) -> Patente:
        """A patente de maior limiar que os pontos alcançam (limiar <= pontos)."""
        return PATENTES[bisect_right(self.limiares, pontos_totais) - 1]

    def falta_para_proxima(self, pontos_totais: int) -> int:
        """O próximo limiar menos os pontos; 0 na última patente."""
        proximo = bisect_right(self.limiares, pontos_totais)
        if proximo == len(self.limiares):
            return 0
        return self.limiares[proximo] - pontos_totais
