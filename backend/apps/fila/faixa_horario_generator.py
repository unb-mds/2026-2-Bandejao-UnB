"""FaixaHorarioGenerator: as faixas de 15 min de uma refeição (RF13, RN06)."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from apps.cardapio.horario_refeicao_resolver import intervalo
from config.parametros import ParametrosFilaConfig


@dataclass(frozen=True)
class FaixaHorario:
    """Faixa no horário local (America/Sao_Paulo), como `Checkin.faixa_inicio`."""

    inicio: time
    fim: time


class FaixaHorarioGenerator:
    def faixas(self, tipo_refeicao: str) -> list[FaixaHorario]:
        """Faixas seguidas do início ao fim da refeição (Anexo A), sem buraco.

        Se o horário não fechar em faixas inteiras, a última termina junto
        com a refeição. As contas são feitas num dia qualquer porque `time`
        não soma `timedelta`.
        """
        inicio, fim = intervalo(tipo_refeicao)
        passo = timedelta(minutes=ParametrosFilaConfig.faixa_minutos)
        atual = datetime.combine(date.min, inicio)
        limite = datetime.combine(date.min, fim)
        faixas = []
        while atual < limite:
            seguinte = min(atual + passo, limite)
            faixas.append(FaixaHorario(inicio=atual.time(), fim=seguinte.time()))
            atual = seguinte
        return faixas
