"""`python manage.py ler_cardapio` (RF06, ADR 0003 e 0014, Leitor N4 4a).

Lê o cardápio de cada campus cadastrado na página do RU e grava no banco,
sem cadastro manual. É um processo periódico, como o
`excluir_cadastros_pendentes`: quem o coloca no cron do SO, de 3 em 3
horas, é a frente de banco (BD-07). No Docker da VM:

    docker compose exec -T backend python manage.py ler_cardapio

O resumo vai para o stdout (o cron grava em log), sem dado de usuário. Se a
leitura de algum campus terminar num erro inesperado, o comando sai com
código 1 (`CommandError`), depois de processar todos os campi.
"""

import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.cardapio.leitor.alerta_equipe_service import AlertaEquipeService
from apps.cardapio.leitor.leitor_cardapio_service import (
    LeitorCardapioService,
    ResultadoLeitura,
)
from apps.cardapio.models import Campus, TipoAlerta

logger = logging.getLogger(__name__)


class LerCardapioCommand:
    def __init__(self):
        self.servico = LeitorCardapioService()

    def executar(
        self, agora: datetime
    ) -> list[tuple[Campus, ResultadoLeitura | Exception]]:
        """Processa cada campus, em ordem de id, com o mesmo `agora`.

        As falhas da leitura, esperadas ou não, já viram alerta dentro do
        serviço, semana a semana. O que ainda escapar do campus (o banco fora
        do ar, um bug fora das semanas) vira log de erro e, se der, alerta à
        equipe; o laço segue para os outros campi, e o `handle` termina com
        erro no fim.
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
                self._alertar_erro_inesperado(campus, exc, agora)
            resultados.append((campus, resultado))
        return resultados

    def _alertar_erro_inesperado(self, campus, exc, agora):
        # `try` próprio: com o banco fora do ar, nem o alerta é gravado, e
        # isso não pode esconder o erro original nem parar os outros campi.
        try:
            alertas = AlertaEquipeService()
            alertas.registrar_alerta(
                TipoAlerta.FALHA_LEITURA_PDF,
                campus,
                f"Etapa: erro inesperado na leitura do campus. "
                f"{type(exc).__name__}: {exc}. Último cardápio válido mantido.",
            )
            alertas.enviar_pendentes(campus, agora=agora)
        except Exception:
            logger.exception(
                "Não foi possível registrar o alerta do erro inesperado do campus %s",
                campus.pk,
            )


class Command(BaseCommand):
    help = "Lê o cardápio dos campi na página do RU e grava no banco (RF06)."

    def handle(self, *args, **options):
        # O relógio é lido uma vez só e vale para todos os campi.
        resultados = LerCardapioCommand().executar(timezone.now())
        if not resultados:
            self.stdout.write("Nenhum campus no banco: nada a ler.")
            return
        falharam = []
        for campus, resultado in resultados:
            if isinstance(resultado, Exception):
                linha = f"erro inesperado ({type(resultado).__name__}: {resultado})"
                falharam.append(f"{campus.nome} ({type(resultado).__name__})")
            else:
                linha = (
                    f"{resultado.lidas} lidas, {resultado.sem_mudanca} sem "
                    f"mudança, {resultado.alertas} alertas"
                )
            self.stdout.write(f"{campus.nome}: {linha}")
        if falharam:
            # Código de saída 1: é por ele que o cron (BD-07) vê a falha.
            raise CommandError(
                f"Erro inesperado na leitura do cardápio: {', '.join(falharam)}."
            )
