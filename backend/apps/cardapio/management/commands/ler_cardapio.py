"""`python manage.py ler_cardapio` (RF06, ADR 0003 e 0014, Leitor N4 4a).

Lê o cardápio de cada campus cadastrado na página do RU e grava no banco,
sem cadastro manual. É um processo periódico, como o
`excluir_cadastros_pendentes`: quem o coloca no cron do SO, de 3 em 3
horas, é a frente de banco (BD-07). No Docker da VM:

    docker compose exec -T backend python manage.py ler_cardapio

O resumo vai para o stdout (o cron grava em log), sem dado de usuário. O
comando sai com código 1 (`CommandError`), depois de processar todos os
campi e enviar os e-mails, se algum campus teve erro inesperado (dentro ou
fora das semanas) ou se o e-mail de alertas de algum campus não saiu.
As falhas esperadas da leitura viram alerta e não mudam o código de saída.
Execuções simultâneas não são suportadas: o cron dispara uma de cada vez, e
duas ao mesmo tempo poderiam passar do limite de e-mails (ADR 0006).
"""

import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

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
        # `try` próprios: com o banco fora do ar, nem o alerta é gravado, e
        # isso não pode esconder o erro original nem parar os outros campi.
        alertas = self.servico.alertas
        try:
            alertas.registrar_alerta(
                TipoAlerta.FALHA_LEITURA_PDF,
                campus,
                f"Etapa: erro inesperado na leitura do campus. "
                f"{type(exc).__name__}: {exc}. Último cardápio válido mantido.",
            )
        except Exception:
            logger.exception(
                "Não foi possível registrar o alerta do erro inesperado do campus %s",
                campus.pk,
            )
            return
        try:
            alertas.enviar_pendentes(campus, agora=agora)
        except Exception:
            logger.exception(
                "Não foi possível enviar o e-mail do alerta do erro inesperado do "
                "campus %s",
                campus.pk,
            )


class Command(BaseCommand):
    help = "Lê o cardápio de cada campus na página do RU e grava no banco (RF06)."

    def handle(self, *args, **options):
        # O relógio é lido uma vez só e vale para todos os campi.
        resultados = LerCardapioCommand().executar(timezone.now())
        if not resultados:
            self.stdout.write("Nenhum campus no banco: nada a ler.")
            return
        falharam = []
        for campus, resultado in resultados:
            linha, problemas = self._resumo(resultado)
            self.stdout.write(f"{campus.nome}: {linha}")
            if problemas:
                falharam.append(f"{campus.nome} ({', '.join(problemas)})")
        if falharam:
            # Código de saída 1: é por ele que o cron (BD-07) vê a falha.
            raise CommandError(f"Falha na leitura do cardápio: {'; '.join(falharam)}.")

    @staticmethod
    def _resumo(resultado):
        """A linha do campus no stdout e o que faz o comando sair com erro."""
        if isinstance(resultado, Exception):
            nome = type(resultado).__name__
            return f"erro inesperado ({nome}: {resultado})", [f"erro inesperado {nome}"]
        partes = [
            f"{resultado.lidas} lidas",
            f"{resultado.sem_mudanca} sem mudança",
            f"{resultado.alertas} alertas",
        ]
        problemas = []
        if resultado.inesperados:
            plural = "s" if resultado.inesperados > 1 else ""
            texto = f"{resultado.inesperados} erro{plural} inesperado{plural}"
            partes.append(texto)
            problemas.append(texto)
        if resultado.email_falhou:
            partes.append("e-mail falhou")
            problemas.append("e-mail de alertas não saiu")
        return ", ".join(partes), problemas
