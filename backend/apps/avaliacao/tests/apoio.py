"""Datas e criação de avaliações para os testes da BE-13."""

from datetime import date, time

from apps.avaliacao.models import Avaliacao
from apps.cardapio.tests.apoio_cardapio import em_brasilia

SEGUNDA = date(2026, 11, 23)
TERCA = date(2026, 11, 24)
QUARTA = date(2026, 11, 25)

# 12h07 de terça em Brasília: o almoço já começou.
DURANTE_O_ALMOCO = em_brasilia(TERCA, time(12, 7))


def avaliar(conta, refeicao, nota=4, comentario=None, oculta=False):
    """Avaliação gravada direto no banco, sem passar pelo serviço."""
    return Avaliacao.objects.create(
        usuario=conta,
        refeicao=refeicao,
        nota=nota,
        comentario=comentario,
        oculta=oculta,
    )
