"""`python manage.py desvincular_registros_fila` (RNF07.3, Fila N4 4d).

Retira a conta, `registrado_em` e `data_hora` dos registros de fila com mais
de 4 semanas (`RetencaoFilaService.desvincular_antigos`). É um processo
periódico, para rodar uma vez por dia: quem o coloca no cron do SO é a BD-07
(#147).
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
        check-in: entre 21h e meia-noite de Brasília, o dia UTC já é o
        seguinte.
        """
        try:
            desvinculados = self.servico.desvincular_antigos(timezone.localdate())
        except Exception:
            # No formato de log do projeto; o erro segue para o comando sair
            # com status diferente de 0, que o cron guarda.
            logger.exception(
                "Falha na retenção dos registros de fila; nada foi alterado."
            )
            raise
        # Só a contagem: o log não leva dado da conta (RNF07).
        logger.info("Registros de fila desvinculados: %s", desvinculados)
        return desvinculados


class Command(BaseCommand):
    help = "Retira a conta dos registros de fila com mais de 4 semanas (RNF07.3)."

    def handle(self, *args, **options):
        desvinculados = DesvincularRegistrosFilaJob().executar()
        self.stdout.write(f"Registros de fila desvinculados: {desvinculados}")
