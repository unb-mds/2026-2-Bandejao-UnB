"""PR de prova da BE-19 (#186): agora com asserções; a porta fica verde."""

import pytest

from apps.gamificacao.prova_mutacao import bonus_por_sequencia


@pytest.mark.parametrize(
    ("dias", "bonus"),
    [(0, 0), (2, 0), (3, 5), (4, 5), (5, 10), (7, 10)],
)
def test_bonus_por_sequencia(dias, bonus):
    assert bonus_por_sequencia(dias) == bonus


def test_bonus_por_sequencia_negativa_e_erro():
    with pytest.raises(ValueError, match=r"^dias_seguidos não pode ser negativo$"):
        bonus_por_sequencia(-1)
