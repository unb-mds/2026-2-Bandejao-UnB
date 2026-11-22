"""JanelaHistoricoResolver: os dias que a previsão olha (RF13, Fila N4 4c)."""

from datetime import date, timedelta

from config.parametros import ParametrosFilaConfig


class JanelaHistoricoResolver:
    def datas_da_janela(self, data: date) -> list[date]:
        """O mesmo dia da semana nas 4 semanas anteriores, da mais recente
        para a mais antiga (Anexo A).

        O próprio `data` fica de fora: hoje a refeição ainda pode estar
        acontecendo, e a previsão é do histórico, não do dia em andamento.
        """
        semanas = ParametrosFilaConfig.janela_semanas
        return [data - timedelta(weeks=n) for n in range(1, semanas + 1)]
