"""JanelaCheckinValidator: o check-in está no horário da refeição? (RF11)."""

from datetime import datetime, time

from django.utils import timezone

from apps.cardapio.models import TipoRefeicao
from config.parametros import HorariosRefeicaoConfig

HORARIOS = {
    TipoRefeicao.CAFE: HorariosRefeicaoConfig.horario_cafe,
    TipoRefeicao.ALMOCO: HorariosRefeicaoConfig.horario_almoco,
    TipoRefeicao.JANTAR: HorariosRefeicaoConfig.horario_jantar,
}


class JanelaCheckinValidator:
    def janela(self, tipo_refeicao: str) -> tuple[time, time]:
        """Início e fim da refeição no horário de Brasília (Anexo A)."""
        return HORARIOS[tipo_refeicao]

    def dentro_do_horario(self, tipo_refeicao: str, agora: datetime) -> bool:
        """Compara no horário local, com início e fim inclusive.

        O fim é o minuto exato do Anexo A: às 14h30 o almoço ainda aceita
        check-in; às 14h30min01s, não.
        """
        inicio, fim = self.janela(tipo_refeicao)
        return inicio <= timezone.localtime(agora).time() <= fim
