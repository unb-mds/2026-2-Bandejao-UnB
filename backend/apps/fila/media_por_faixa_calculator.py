"""MediaPorFaixaCalculator: média de check-ins de cada faixa (RN06)."""

from fractions import Fraction

from apps.fila.checkin_repository import ContagemDia


class MediaPorFaixaCalculator:
    def calcular(self, contagens: list[ContagemDia]) -> list[Fraction]:
        """Média de cada faixa só nos dias com dados (RN06, decisão do grupo).

        `contagens` traz só os dias com check-in; nesses dias, a faixa vazia
        entra como zero. A média é uma fração exata: com float, um corte de
        75% ou um empate poderiam se perder no arredondamento.
        """
        dias = len(contagens)
        totais = [
            sum(faixa) for faixa in zip(*(c.checkins_por_faixa for c in contagens))
        ]
        return [Fraction(total, dias) for total in totais]
