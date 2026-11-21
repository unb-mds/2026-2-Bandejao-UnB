"""`python manage.py ler_cardapio` (RF06, ADR 0003 e 0014, Leitor N4 4a).

Lê o cardápio dos 5 campi na página do RU e grava no banco, sem cadastro
manual. É um processo periódico, como o `excluir_cadastros_pendentes`: quem
o coloca no cron do SO, de 3 em 3 horas, é a frente de banco (BD-07). No
Docker da VM:

    docker compose exec -T backend python manage.py ler_cardapio

O resumo vai para o stdout (o cron grava em log), sem dado de usuário.
"""

import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cardapio.leitor.leitor_cardapio_service import (
    LeitorCardapioService,
    ResultadoLeitura,
)
from apps.cardapio.models import Campus

logger = logging.getLogger(__name__)


class LerCardapioCommand:
    def __init__(self):
        self.servico = LeitorCardapioService()

    def executar(
        self, agora: datetime
    ) -> list[tuple[Campus, ResultadoLeitura | Exception]]:
        """Processa cada campus, em ordem de id, com o mesmo `agora`.

        A falha inesperada de um campus (um bug, o banco fora do ar) vira
        log de erro, e o laço segue para os outros. As falhas esperadas da
        leitura já viram alerta dentro do serviço.
        """
        resultados = []
        for campus in Campus.objects.order_by("id"):
            try:
                resultado = self.servico.processar(campus, agora)
            except Exception as exc:
                # Qualquer exceção: um campus não para os outros. O traceback
                # vai para o log (o Leitor não lida com dado de usuário).
                logger.exception(
                    "Erro inesperado na leitura do cardápio do campus %s: %s",
                    campus.pk,
                    type(exc).__name__,
                )
                resultado = exc
            resultados.append((campus, resultado))
        return resultados


class Command(BaseCommand):
    help = "Lê o cardápio dos campi na página do RU e grava no banco (RF06)."

    def handle(self, *args, **options):
        # O relógio é lido uma vez só e vale para todos os campi.
        resultados = LerCardapioCommand().executar(timezone.now())
        if not resultados:
            self.stdout.write("Nenhum campus no banco: nada a ler.")
            return
        for campus, resultado in resultados:
            if isinstance(resultado, Exception):
                linha = f"erro inesperado ({type(resultado).__name__})"
            else:
                linha = (
                    f"{resultado.lidas} lidas, {resultado.sem_mudanca} sem "
                    f"mudança, {resultado.alertas} alertas"
                )
            self.stdout.write(f"{campus.nome}: {linha}")
