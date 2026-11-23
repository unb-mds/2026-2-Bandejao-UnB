"""Testes do código da prova da BE-18 (#187), que nunca vai para a develop.

Cada etapa soma 1 ao valor e depois faz oito vezes "dobra e tira k", com k
o número da etapa. Pela forma fechada, o resultado é 256 * (valor + 1) -
255 * k, conta diferente da do código.
"""

import pytest

from apps.avaliacao import prova_cobertura


@pytest.mark.parametrize("numero", range(1, 16))
@pytest.mark.parametrize("valor", [0, 3, -1])
def test_etapa_segue_a_forma_fechada(numero, valor):
    etapa = getattr(prova_cobertura, f"etapa_{numero:02d}")

    assert etapa(valor) == 256 * (valor + 1) - 255 * numero
