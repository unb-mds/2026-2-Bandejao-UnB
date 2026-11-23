"""PR de prova da BE-19 (#186): teste sem asserção. Passa, cobre todas as
linhas e não testa nada; a porta de mutação tem que barrar."""

import pytest

from apps.gamificacao.prova_mutacao import bonus_por_sequencia


def test_bonus_por_sequencia():
    for dias in (0, 2, 3, 4, 5, 7):
        bonus_por_sequencia(dias)
    with pytest.raises(ValueError):
        bonus_por_sequencia(-1)
