"""`python manage.py desvincular_registros_fila` (RNF07.3, Fila N4 4d).

Retira a conta e a hora exata dos registros de fila com mais de 4 semanas
(`RetencaoFilaService.desvincular_antigos`). Roda uma vez por dia, no cron do
SO configurado pela BD-07 (#147), junto dos outros comandos periódicos.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.fila.retencao_fila_service import RetencaoFilaService

logger = logging.getLogger(__name__)


class DesvincularRegistrosFilaJob:
    def __init__(self, servico: RetencaoFilaService | None = None):
        self.servico = servico or RetencaoFilaService()

    def executar(self) -> int:
        """Desvincula os registros antigos e devolve quantos foram.

        O prazo conta do dia de Brasília (`TIME_ZONE`), o mesmo da `data` do
        check-in: perto da meia-noite, o dia UTC já é o seguinte.
        """
        desvinculados = self.servico.desvincular_antigos(timezone.localdate())
        # Só a contagem: o log não leva dado da conta (RNF07).
        logger.info("Registros de fila desvinculados: %s", desvinculados)
        return desvinculados


class Command(BaseCommand):
    help = "Retira a conta dos registros de fila com mais de 4 semanas (RNF07.3)."

    def handle(self, *args, **options):
        desvinculados = DesvincularRegistrosFilaJob().executar()
        self.stdout.write(f"Registros de fila desvinculados: {desvinculados}")
