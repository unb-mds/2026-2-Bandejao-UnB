"""PatenteResolver: a patente e o que falta para a próxima (BE-16, RF26.1, RN11).

A patente é a de maior limiar que os pontos totais alcançam, e o que falta é o
próximo limiar menos os pontos (0 na última). Os limiares vêm da
`ParametrosGamificacaoConfig` (Anexo A); os testes de regra passam limiares
próprios pelo construtor, para provar que nada está fixo no código.
"""

import pytest

from apps.gamificacao.patente import Patente
from apps.gamificacao.patente_resolver import PatenteResolver
from config.parametros import ParametrosGamificacaoConfig

CALOURO = Patente.CALOURO_DE_BANDEJA
RATO = Patente.RATO_DE_RU
VETERANO = Patente.VETERANO
MESTRE = Patente.MESTRE_DA_FILA
LENDA = Patente.LENDA_DO_RU

ORDEM = list(Patente)


def posicao(patente):
    return ORDEM.index(patente)


# --- Config real: cada limiar e o ponto logo abaixo (5.1 #1, #2) -------------


@pytest.mark.parametrize(
    ("pontos", "patente", "falta"),
    [
        (0, CALOURO, 150),
        (149, CALOURO, 1),
        (150, RATO, 300),
        (449, RATO, 1),
        (450, VETERANO, 450),
        (899, VETERANO, 1),
        (900, MESTRE, 600),
        (1499, MESTRE, 1),
        (1500, LENDA, 0),
        (10000, LENDA, 0),
    ],
)
def test_patente_e_falta_em_cada_limiar_e_logo_abaixo(pontos, patente, falta):
    resolver = PatenteResolver()

    assert resolver.patente(pontos) == patente
    assert resolver.falta_para_proxima(pontos) == falta


def test_150_pontos_e_rato_de_ru_exemplo_do_rf26_1():
    assert PatenteResolver().patente(150) == RATO


# --- Limiares pelo construtor (5.1 #3) ---------------------------------------


@pytest.mark.parametrize(
    ("pontos", "patente", "falta"),
    [
        (0, CALOURO, 10),
        (9, CALOURO, 1),
        (10, RATO, 10),
        (19, RATO, 1),
        (20, VETERANO, 10),
        (30, MESTRE, 10),
        (39, MESTRE, 1),
        (40, LENDA, 0),
        (150, LENDA, 0),
    ],
)
def test_limiares_proprios_pelo_construtor(pontos, patente, falta):
    resolver = PatenteResolver(limiares=(0, 10, 20, 30, 40))

    assert resolver.patente(pontos) == patente
    assert resolver.falta_para_proxima(pontos) == falta


def test_sem_argumento_le_os_limiares_da_config():
    assert PatenteResolver().limiares == ParametrosGamificacaoConfig.limiares_patente


# --- Não regride (5.1 #5) ----------------------------------------------------


@pytest.mark.parametrize(
    "limiares",
    [ParametrosGamificacaoConfig.limiares_patente, (0, 10, 20, 30, 40)],
    ids=["config", "proprios"],
)
def test_patente_nao_regride_e_falta_so_diminui_dentro_da_patente(limiares):
    """Propriedade para todo `p` de 0 a 2000, sem `hypothesis`."""
    resolver = PatenteResolver(limiares=limiares)

    for pontos in range(2000):
        atual, seguinte = resolver.patente(pontos), resolver.patente(pontos + 1)
        assert posicao(seguinte) >= posicao(atual), pontos
        assert posicao(seguinte) - posicao(atual) <= 1, pontos
        if seguinte == atual:
            assert resolver.falta_para_proxima(
                pontos + 1
            ) <= resolver.falta_para_proxima(pontos), pontos


# --- Sanidade do construtor (5.1 #6) -----------------------------------------


@pytest.mark.parametrize(
    "limiares",
    [
        (0, 450, 150, 900, 1500),
        (0, 150, 150, 900, 1500),
        (10, 150, 450, 900, 1500),
        (0, 150, 450, 900),
        (0, 150, 450, 900, 1500, 3000),
        (),
    ],
    ids=[
        "fora-de-ordem",
        "repetido",
        "primeiro-nao-zero",
        "faltando-um",
        "sobrando-um",
        "vazio",
    ],
)
def test_limiares_invalidos_levantam_value_error(limiares):
    with pytest.raises(ValueError):
        PatenteResolver(limiares=limiares)


# --- Sanidade da config real (5.1 #7) ----------------------------------------


def test_config_tem_um_limiar_por_patente_crescente_a_partir_de_zero():
    limiares = ParametrosGamificacaoConfig.limiares_patente

    assert len(limiares) == len(Patente) == 5
    assert limiares[0] == 0
    assert list(limiares) == sorted(set(limiares))


def test_patentes_na_ordem_dos_limiares_com_os_valores_do_contrato():
    assert [patente.value for patente in Patente] == [
        "CALOURO_DE_BANDEJA",
        "RATO_DE_RU",
        "VETERANO",
        "MESTRE_DA_FILA",
        "LENDA_DO_RU",
    ]
