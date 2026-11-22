"""JanelaAvaliacaoValidator: a refeição pode ser avaliada agora? (RF15.1)."""

from datetime import datetime

from django.utils import timezone

from apps.cardapio.horario_refeicao_resolver import intervalo
from apps.cardapio.models import Refeicao


class JanelaAvaliacaoValidator:
    def pode_avaliar(self, refeicao: Refeicao, agora: datetime) -> bool:
        """Só a refeição do dia corrente que já começou, no horário local.

        Abre no minuto de início do Anexo A (o mesmo parâmetro do
        `HorarioRefeicaoResolver`, e não o horário copiado na refeição) e
        fica aberta até 23h59: à meia-noite a refeição deixa de ser do dia
        corrente. A edição tem a mesma janela (Avaliação N4, notas do 4a).
        """
        local = timezone.localtime(agora)
        inicio, _ = intervalo(refeicao.tipo)
        return refeicao.data == local.date() and local.time() >= inicio
