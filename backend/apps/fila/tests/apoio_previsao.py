"""Datas e check-ins montados para os testes da previsão (BE-15).

O dia da previsão é uma quarta-feira; a janela são as 4 quartas anteriores
(RF13, `ParametrosFilaConfig.janela_semanas`). Os check-ins são gravados direto
no banco e sem conta, como ficam depois da retenção (RNF07.3): a previsão
conta todos, com ou sem vínculo.
"""

from datetime import date, timedelta

from apps.cardapio.models import TipoRefeicao
from apps.fila.models import Checkin

QUARTA = date(2026, 11, 25)
# As 4 quartas da janela, da mais recente para a mais antiga.
JANELA = [QUARTA - timedelta(weeks=n) for n in (1, 2, 3, 4)]
UMA, DUAS, TRES, QUATRO = JANELA
# Fora da janela: a 5ª quarta para trás e a terça da semana passada.
CINCO_SEMANAS = QUARTA - timedelta(weeks=5)
TERCA_PASSADA = UMA - timedelta(days=1)


def checkins(campus, dia, faixa, quantidade=1, tipo=TipoRefeicao.ALMOCO):
    """`quantidade` check-ins confirmados na `faixa` de `dia`, sem conta."""
    Checkin.objects.bulk_create(
        Checkin(campus=campus, tipo_refeicao=tipo, data=dia, faixa_inicio=faixa)
        for _ in range(quantidade)
    )


def mesmo_movimento(campus, dias, por_faixa, tipo=TipoRefeicao.ALMOCO):
    """Repete em cada dia de `dias` as quantidades de `por_faixa`
    ({faixa: quantidade})."""
    for dia in dias:
        for faixa, quantidade in por_faixa.items():
            checkins(campus, dia, faixa, quantidade, tipo)
