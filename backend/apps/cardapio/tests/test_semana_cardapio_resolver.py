"""SemanaCardapioResolver e Semana (BE-11, RF07.1, RF18, Exposição N4 4a).

Decisão de 21/11/2026 (guia da BE-11, 5.5): a semana vem da `FonteCardapio`,
uma linha por PDF lido com sucesso. A semana de um dia é a linha do campus
cujo intervalo `[semana_inicio, semana_inicio + 6 dias]` contém o dia. Sem
linha, a semana não está publicada, mesmo com `Refeicao` no banco (sem
fallback pelas refeições). Na Release 2 só a semana vigente é entregue.
"""

from datetime import timedelta

import pytest

from apps.cardapio.semana_cardapio_resolver import Semana, SemanaCardapioResolver
from apps.cardapio.tests.apoio_cardapio import (
    DOMINGO,
    PROXIMA_SEGUNDA,
    SEGUNDA,
    TERCA,
    criar_campus,
    criar_refeicao,
    publicar_semana,
)

SEMANA_23_11 = Semana(inicio=SEGUNDA, fim=DOMINGO, vigente=True)


@pytest.fixture
def campus(db):
    return criar_campus()


@pytest.fixture
def resolver():
    return SemanaCardapioResolver()


def test_dia_dentro_do_intervalo_devolve_a_semana(campus, resolver):
    publicar_semana(campus, SEGUNDA)

    assert resolver.semanas_disponiveis(campus, TERCA) == [SEMANA_23_11]


@pytest.mark.parametrize("dia", [SEGUNDA, DOMINGO])
def test_primeiro_e_ultimo_dia_do_intervalo_estao_dentro(campus, resolver, dia):
    publicar_semana(campus, SEGUNDA)

    assert resolver.semanas_disponiveis(campus, dia) == [SEMANA_23_11]


@pytest.mark.parametrize(
    "dia", [SEGUNDA - timedelta(days=1), DOMINGO + timedelta(days=1)]
)
def test_dia_fora_de_qualquer_linha_nao_tem_semana(campus, resolver, dia):
    publicar_semana(campus, SEGUNDA)

    assert resolver.semanas_disponiveis(campus, dia) == []


def test_campus_com_refeicao_mas_sem_fonte_cardapio_nao_tem_semana(campus, resolver):
    criar_refeicao(campus, TERCA)

    assert resolver.semanas_disponiveis(campus, TERCA) == []


def test_fonte_de_outro_campus_nao_conta(campus, resolver):
    publicar_semana(criar_campus("Ceilândia"), SEGUNDA)

    assert resolver.semanas_disponiveis(campus, TERCA) == []


def test_com_a_semana_seguinte_lida_entrega_so_a_do_dia(campus, resolver):
    # RF18 (semana seguinte) fica fora da BE-11: mesmo com as duas linhas,
    # a resposta é só a semana que contém o dia.
    publicar_semana(campus, SEGUNDA)
    publicar_semana(campus, PROXIMA_SEGUNDA)

    assert resolver.semanas_disponiveis(campus, TERCA) == [SEMANA_23_11]
    assert resolver.semanas_disponiveis(campus, PROXIMA_SEGUNDA) == [
        Semana(
            inicio=PROXIMA_SEGUNDA,
            fim=PROXIMA_SEGUNDA + timedelta(days=6),
            vigente=True,
        )
    ]


def test_semana_tem_inicio_fim_e_vigente():
    semana = Semana(inicio=SEGUNDA, fim=DOMINGO, vigente=True)

    assert (semana.inicio, semana.fim, semana.vigente) == (SEGUNDA, DOMINGO, True)
    assert (semana.fim - semana.inicio).days == 6
