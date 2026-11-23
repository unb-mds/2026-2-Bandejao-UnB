"""SuficienciaDadosValidator: há dias suficientes para a previsão? (RF13, RN06)."""

from apps.fila.checkin_repository import ContagemDia
from config.parametros import ParametrosFilaConfig


class SuficienciaDadosValidator:
    def suficiente(self, contagens: list[ContagemDia]) -> bool:
        """Pelo menos 3 dias distintos com check-in na janela (Anexo A).

        Conta dias, não check-ins: muitos check-ins num dia só não liberam a
        previsão. Roda antes da média, o que garante ao classificador uma
        faixa mais cheia com média maior que zero.
        """
        dias_com_dados = {c.data for c in contagens if any(c.checkins_por_faixa)}
        return len(dias_com_dados) >= ParametrosFilaConfig.min_dias_distintos
