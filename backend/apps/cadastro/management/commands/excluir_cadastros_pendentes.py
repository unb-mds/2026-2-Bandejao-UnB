"""`python manage.py excluir_cadastros_pendentes` (RF02.3, Cadastro N4 4b).

Apaga o cadastro pendente sem confirmação nem reenvio há mais de 24 h, o que
libera a matrícula/SIAPE e o e-mail para um cadastro novo.

É um processo periódico, separado do `CadastroService`, como o leitor do
cardápio: quem o coloca no cron do SO é a frente de banco (BD-07), junto do
`clearsessions` do Django (ADR 0007).
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cadastro.confirmacao_email_service import VALIDADE_DO_LINK
from apps.cadastro.conta_repository import ContaRepository

logger = logging.getLogger(__name__)


class ExclusaoCadastroPendenteJob:
    def __init__(self):
        self.conta_repository = ContaRepository()

    def executar(self) -> int:
        """Apaga as contas pendentes expiradas e devolve quantas foram."""
        limite = timezone.now() - VALIDADE_DO_LINK
        excluidas = 0
        # Lista antes de apagar (apagar no meio de um cursor aberto dá problema
        # no SQLite). Uma conta por vez: cada exclusão confere o prazo de novo,
        # na própria transação, então um reenvio no meio do job é respeitado.
        for conta in list(self.conta_repository.pendentes_expiradas(limite)):
            if self.conta_repository.excluir_pendente_expirada(conta, limite):
                excluidas += 1
        # Só a contagem: o log não leva matrícula nem e-mail (RNF07).
        logger.info("Cadastros pendentes expirados excluídos: %s", excluidas)
        return excluidas


class Command(BaseCommand):
    help = "Exclui os cadastros pendentes não confirmados no prazo (RF02.3)."

    def handle(self, *args, **options):
        excluidas = ExclusaoCadastroPendenteJob().executar()
        self.stdout.write(f"Cadastros pendentes excluídos: {excluidas}")
