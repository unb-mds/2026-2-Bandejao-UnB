"""PrevisaoService e CheckinRepository.contar_por_faixa (BE-15, RF13, RN06,
Fila N4 4c).

Dados montados direto no banco (`apoio_previsao`): abaixo e no mínimo de
dias, empate, faixa zerada, outro dia da semana e a leitura de "dias com
dados" da RN06.
"""

from datetime import time

from apps.cardapio.models import TipoRefeicao
from apps.fila.checkin_repository import CheckinRepository, ContagemDia
from apps.fila.classificador_nivel_fila import NivelFila
from apps.fila.faixa_horario_generator import FaixaHorarioGenerator
from apps.fila.models import Checkin
from apps.fila.previsao_service import PrevisaoService, StatusPrevisao
from apps.fila.tests.apoio_previsao import (
    CINCO_SEMANAS,
    DUAS,
    JANELA,
    QUARTA,
    QUATRO,
    TERCA_PASSADA,
    TRES,
    UMA,
    checkins,
    mesmo_movimento,
)

ALMOCO = TipoRefeicao.ALMOCO
H11_00, H11_15, H11_30, H11_45, H12_00 = (
    time(11, 0),
    time(11, 15),
    time(11, 30),
    time(11, 45),
    time(12, 0),
)


def calcular(campus, tipo=ALMOCO, data=QUARTA):
    return PrevisaoService().calcular(campus, tipo, data)


def por_inicio(previsao):
    return {faixa.inicio: faixa for faixa in previsao.faixas}


# --- CheckinRepository.contar_por_faixa ---------------------------------------


def contar(campus, tipo=ALMOCO, datas=JANELA):
    faixas = FaixaHorarioGenerator().faixas(tipo)
    return CheckinRepository().contar_por_faixa(campus, tipo, datas, faixas)


def test_contagem_devolve_so_os_dias_com_checkin_na_ordem_da_janela(darcy):
    checkins(darcy, TRES, H11_15, 2)
    checkins(darcy, UMA, H11_00)

    contagens = contar(darcy)

    assert [c.data for c in contagens] == [UMA, TRES]
    assert contagens[1] == ContagemDia(data=TRES, checkins_por_faixa=[0, 2] + [0] * 12)


def test_contagem_ignora_outro_campus_outra_refeicao_e_fora_da_janela(darcy, gama):
    checkins(gama, UMA, H11_00)
    checkins(darcy, UMA, time(18, 0), tipo=TipoRefeicao.JANTAR)
    checkins(darcy, CINCO_SEMANAS, H11_00)
    checkins(darcy, TERCA_PASSADA, H11_00)

    assert contar(darcy) == []


def test_checkin_no_minuto_final_entra_na_ultima_faixa(darcy):
    """O check-in vale até as 14h30 inclusive (JanelaCheckinValidator), e a
    faixa dele começa às 14h30: entra na faixa 14h15-14h30."""
    checkins(darcy, UMA, time(14, 30))

    (contagem,) = contar(darcy)

    assert contagem.checkins_por_faixa[-1] == 1


def test_checkins_das_14h15_e_das_14h30_somam_na_ultima_faixa(darcy):
    """Duas linhas do agrupamento caem na mesma faixa: somam, não se
    sobrescrevem."""
    checkins(darcy, UMA, time(14, 15), 2)
    checkins(darcy, UMA, time(14, 30), 3)

    (contagem,) = contar(darcy)

    assert contagem.checkins_por_faixa[-1] == 5


def test_checkin_fora_das_faixas_da_refeicao_nao_e_contado(darcy):
    """Só acontece se o horário do Anexo A mudar depois do check-in."""
    checkins(darcy, UMA, time(10, 45))
    checkins(darcy, UMA, time(14, 45))

    assert contar(darcy) == []


def test_contagem_inclui_checkins_que_ja_perderam_a_conta(darcy, conta):
    """A retenção (RNF07.3) só tira o vínculo; o registro continua contando."""
    checkins(darcy, UMA, H11_00)  # sem conta
    Checkin.objects.create(
        usuario=conta,
        campus=darcy,
        tipo_refeicao=ALMOCO,
        data=UMA,
        faixa_inicio=H11_00,
    )

    (contagem,) = contar(darcy)

    assert contagem.checkins_por_faixa[0] == 2


def test_contagem_faz_uma_consulta_so(darcy, django_assert_num_queries):
    mesmo_movimento(darcy, JANELA, {H11_00: 1, H12_00: 2})

    with django_assert_num_queries(1):
        contar(darcy)


# --- Suficiência: abaixo e no mínimo de dias -----------------------------------


def test_dois_dias_com_dados_dao_dados_insuficientes_sem_faixas(darcy):
    mesmo_movimento(darcy, [UMA, DUAS], {H11_00: 5, H11_15: 9})

    previsao = calcular(darcy)

    assert previsao.status is StatusPrevisao.DADOS_INSUFICIENTES
    assert previsao.faixas == []


def test_tres_dias_com_dados_liberam_a_previsao(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {H11_00: 1})

    previsao = calcular(darcy)

    assert previsao.status is StatusPrevisao.DISPONIVEL
    assert len(previsao.faixas) == 14


def test_sem_nenhum_checkin_da_dados_insuficientes(darcy):
    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES


def test_muitos_checkins_num_dia_so_nao_bastam(darcy):
    """O mínimo é de dias distintos, não de check-ins (RF13)."""
    checkins(darcy, UMA, H11_00, 200)
    checkins(darcy, DUAS, H11_00, 200)

    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES


# --- Outro dia da semana, outro campus e outra refeição não contam --------------


def test_checkins_de_outro_dia_da_semana_nao_contam_para_a_suficiencia(darcy):
    mesmo_movimento(darcy, [UMA, DUAS], {H11_00: 3})
    checkins(darcy, TERCA_PASSADA, H11_00, 3)

    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES


def test_checkins_de_outro_dia_da_semana_nao_mudam_o_nivel(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {H11_00: 4, H11_15: 1})
    checkins(darcy, TERCA_PASSADA, H11_15, 50)

    faixas = por_inicio(calcular(darcy))

    assert faixas[H11_00].eh_pico is True
    assert faixas[H11_15].nivel is NivelFila.CURTA


def test_quinta_semana_para_tras_fica_fora_da_janela(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, CINCO_SEMANAS], {H11_00: 2})

    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES


def test_checkins_do_proprio_dia_nao_entram(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, QUARTA], {H11_00: 2})

    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES


def test_previsao_de_um_campus_ignora_o_outro(darcy, gama):
    mesmo_movimento(gama, [UMA, DUAS, TRES], {H11_00: 2})

    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES
    assert calcular(gama).status is StatusPrevisao.DISPONIVEL


def test_previsao_do_almoco_ignora_o_jantar(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {time(18, 0): 2}, TipoRefeicao.JANTAR)

    assert calcular(darcy).status is StatusPrevisao.DADOS_INSUFICIENTES
    assert calcular(darcy, TipoRefeicao.JANTAR).status is StatusPrevisao.DISPONIVEL


# --- Níveis, pico e empate ------------------------------------------------------


def test_niveis_relativos_a_faixa_mais_cheia(darcy):
    """Médias 8, 6, 4, 2 e 1 contra a maior, 8: 100%, 75%, 50%, 25% e 12,5%."""
    mesmo_movimento(
        darcy,
        [UMA, DUAS, TRES],
        {H11_00: 1, H11_15: 2, H11_30: 4, H11_45: 6, H12_00: 8},
    )

    faixas = por_inicio(calcular(darcy))

    assert faixas[H12_00].nivel is NivelFila.LONGA
    assert faixas[H11_45].nivel is NivelFila.LONGA
    assert faixas[H11_30].nivel is NivelFila.MODERADA
    assert faixas[H11_15].nivel is NivelFila.CURTA
    assert faixas[H11_00].nivel is NivelFila.VAZIA


def test_so_a_faixa_mais_cheia_e_pico(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {H11_45: 6, H12_00: 8})

    picos = [faixa.inicio for faixa in calcular(darcy).faixas if faixa.eh_pico]

    assert picos == [H12_00]


def test_empate_todas_as_faixas_mais_cheias_sao_pico_e_longas(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {H11_15: 5, H12_00: 5, H11_30: 4})

    previsao = calcular(darcy)
    picos = [faixa for faixa in previsao.faixas if faixa.eh_pico]

    assert [faixa.inicio for faixa in picos] == [H11_15, H12_00]
    assert {faixa.nivel for faixa in picos} == {NivelFila.LONGA}
    # 4 de 5 é longa, mas não é pico.
    assert por_inicio(previsao)[H11_30].nivel is NivelFila.LONGA
    assert por_inicio(previsao)[H11_30].eh_pico is False


def test_empate_com_medias_fracionarias(darcy):
    """7/3 nas duas faixas, montado com dias diferentes em cada uma."""
    checkins(darcy, UMA, H11_00, 3)
    checkins(darcy, DUAS, H11_00, 4)
    checkins(darcy, TRES, H11_30, 5)
    checkins(darcy, UMA, H11_30, 2)

    picos = [f.inicio for f in calcular(darcy).faixas if f.eh_pico]

    assert picos == [H11_00, H11_30]


def test_faixa_zerada_e_vazia_e_nao_e_pico(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {H12_00: 3})

    faixas = por_inicio(calcular(darcy))

    assert faixas[H11_00].nivel is NivelFila.VAZIA
    assert faixas[H11_00].eh_pico is False
    assert faixas[time(14, 15)].nivel is NivelFila.VAZIA


def test_faixa_vazia_nos_dias_com_dados_conta_como_zero(darcy):
    """Um dia atípico com 9 às 11h15 não faz dela o pico: a média é 9/4, e a
    das 11h00, com 3 nos quatro dias, é 3 (RN06, decisão do grupo)."""
    mesmo_movimento(darcy, JANELA, {H11_00: 3})
    checkins(darcy, QUATRO, H11_15, 9)

    faixas = por_inicio(calcular(darcy))

    assert faixas[H11_00].eh_pico is True
    assert faixas[H11_15].eh_pico is False
    assert faixas[H11_15].nivel is NivelFila.LONGA  # 2,25 de 3 = 75%


def test_faixas_saem_na_ordem_do_horario_com_inicio_e_fim(darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {H11_00: 1})

    faixas = calcular(darcy).faixas

    assert [(f.inicio, f.fim) for f in faixas] == [
        (g.inicio, g.fim) for g in FaixaHorarioGenerator().faixas(ALMOCO)
    ]


def test_previsao_leva_campus_refeicao_e_data_pedidos(darcy):
    previsao = calcular(darcy, TipoRefeicao.CAFE)

    assert (previsao.campus, previsao.tipo_refeicao, previsao.data) == (
        darcy,
        TipoRefeicao.CAFE,
        QUARTA,
    )
