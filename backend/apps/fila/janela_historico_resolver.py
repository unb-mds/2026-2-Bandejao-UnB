"""JanelaHistoricoResolver: os dias que a previsão olha (RF13, Fila N4 4c)."""

from datetime import date, timedelta

from config.parametros import ParametrosFilaConfig


class JanelaHistoricoResolver:
    def datas_da_janela(self, data: date, hoje: date) -> list[date]:
        """O mesmo dia da semana nas 4 semanas anteriores, da mais recente
        para a mais antiga (Anexo A), só com os dias que já passaram.

        Hoje fica de fora: a refeição ainda pode estar acontecendo, e a
        previsão é do histórico, não do dia em andamento. Vale também para
        uma data futura, cuja janela começaria em hoje ou depois (revisão do
        #236); bem à frente, a janela fica vazia e a previsão sai com dados
        insuficientes.
        """
        semanas = ParametrosFilaConfig.janela_semanas
        datas = [data - timedelta(weeks=n) for n in range(1, semanas + 1)]
        return [d for d in datas if d < hoje]
