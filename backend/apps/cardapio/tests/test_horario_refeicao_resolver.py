"""HorarioRefeicaoResolver: a RN05 da Release 2 com horário simulado (BE-11).

O resolver nunca lê o relógio: cada teste passa o `agora`. Os valores
esperados foram tirados da RN05 (Anexo B) e dos horários do Anexo A
(café 7h00–9h30, almoço 11h00–14h30, jantar 17h00–19h30), não da saída do
código. Início e fim incluídos (decisão de 21/11/2026, a mesma comparação
do JanelaCheckinValidator da fila): às 9h30min00s ainda é café;
1 s depois, não.

O caso do domingo (RN05, item 5) depende do banco (próximo dia com
serviço) e está em test_cardapio_query_service.py.
"""

from datetime import UTC, date, datetime, time, timedelta

import pytest

from apps.cardapio.horario_refeicao_resolver import (
    HorarioRefeicaoResolver,
    RefeicaoPadrao,
)
from apps.cardapio.models import Refeicao, TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import TERCA, em_brasilia
from apps.fila.janela_checkin_validator import JanelaCheckinValidator
from config.parametros import HorariosRefeicaoConfig

CAFE = TipoRefeicao.CAFE
ALMOCO = TipoRefeicao.ALMOCO
JANTAR = TipoRefeicao.JANTAR
QUARTA = TERCA + timedelta(days=1)


def refeicoes(dia, *tipos):
    """Refeições do dia sem banco: o resolver só lê `data` e `tipo`."""
    return [Refeicao(data=dia, tipo=tipo) for tipo in tipos]


TRES = refeicoes(TERCA, CAFE, ALMOCO, JANTAR)


@pytest.fixture
def resolver():
    return HorarioRefeicaoResolver()


# --- Tabela 9.2 do guia (campus com café, almoço e jantar no dia) -----------


@pytest.mark.parametrize(
    "hora, tipo, encerrada",
    [
        (time(6, 59), CAFE, False),  # próxima
        (time(7, 0), CAFE, False),  # em andamento, início incluído
        (time(9, 30), CAFE, False),  # fim incluído
        (time(9, 31), ALMOCO, False),  # próxima
        (time(10, 0), ALMOCO, False),  # próxima
        (time(12, 0), ALMOCO, False),  # em andamento
        (time(14, 30), ALMOCO, False),  # fim incluído
        (time(14, 31), JANTAR, False),  # próxima
        (time(15, 0), JANTAR, False),  # próxima
        (time(17, 0), JANTAR, False),  # em andamento
        (time(19, 30), JANTAR, False),  # fim incluído
        (time(19, 31), JANTAR, True),  # última do dia, encerrada
        (time(23, 59), JANTAR, True),  # até as 23h59
    ],
)
def test_refeicao_padrao_ao_longo_do_dia(resolver, hora, tipo, encerrada):
    padrao = resolver.refeicao_padrao(em_brasilia(TERCA, hora), TRES)

    assert padrao == RefeicaoPadrao(refeicao=tipo, dia=TERCA, encerrada=encerrada)


def test_depois_da_meia_noite_o_cafe_do_novo_dia_e_o_padrao(resolver):
    # RN05, item 4: às 00h00 de quarta, a refeição padrão é o café de quarta,
    # e não o jantar encerrado de terça.
    padrao = resolver.refeicao_padrao(
        em_brasilia(QUARTA, time(0, 0)), refeicoes(QUARTA, CAFE, ALMOCO, JANTAR)
    )

    assert padrao == RefeicaoPadrao(refeicao=CAFE, dia=QUARTA, encerrada=False)


def test_dia_so_com_almoco_depois_do_almoco_mostra_o_almoco_encerrado(resolver):
    padrao = resolver.refeicao_padrao(
        em_brasilia(TERCA, time(16, 0)), refeicoes(TERCA, ALMOCO)
    )

    assert padrao == RefeicaoPadrao(refeicao=ALMOCO, dia=TERCA, encerrada=True)


def test_dia_sem_cafe_as_8h_mostra_o_almoco_como_proxima(resolver):
    # Os dias e as refeições servidos são os do PDF (RF06.2): o café do
    # Anexo A não vale se o PDF não traz café nesse dia.
    padrao = resolver.refeicao_padrao(
        em_brasilia(TERCA, time(8, 0)), refeicoes(TERCA, ALMOCO, JANTAR)
    )

    assert padrao == RefeicaoPadrao(refeicao=ALMOCO, dia=TERCA, encerrada=False)


def test_dia_sem_jantar_entre_as_refeicoes_fica_encerrado_no_almoco(resolver):
    padrao = resolver.refeicao_padrao(
        em_brasilia(TERCA, time(15, 0)), refeicoes(TERCA, CAFE, ALMOCO)
    )

    assert padrao == RefeicaoPadrao(refeicao=ALMOCO, dia=TERCA, encerrada=True)


def test_ordem_das_refeicoes_recebidas_nao_importa(resolver):
    fora_de_ordem = refeicoes(TERCA, JANTAR, CAFE, ALMOCO)

    assert resolver.refeicao_padrao(
        em_brasilia(TERCA, time(6, 0)), fora_de_ordem
    ) == RefeicaoPadrao(refeicao=CAFE, dia=TERCA, encerrada=False)
    assert resolver.ultima_refeicao_do_dia(fora_de_ordem) == JANTAR


def test_agora_em_utc_e_convertido_para_brasilia(resolver):
    # 12h00 UTC = 9h00 em Brasília: café em andamento, não almoço.
    agora = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)

    padrao = resolver.refeicao_padrao(agora, TRES)

    assert padrao == RefeicaoPadrao(refeicao=CAFE, dia=TERCA, encerrada=False)


def test_virada_do_dia_em_utc_usa_o_dia_de_brasilia(resolver):
    # 02h00 UTC de quarta = 23h00 de terça em Brasília: jantar encerrado.
    agora = datetime(2026, 11, 25, 2, 0, tzinfo=UTC)

    padrao = resolver.refeicao_padrao(agora, TRES)

    assert padrao == RefeicaoPadrao(refeicao=JANTAR, dia=TERCA, encerrada=True)


# --- Dia diferente de hoje ---------------------------------------------------


def test_dia_futuro_mostra_a_primeira_refeicao_nao_encerrada(resolver):
    padrao = resolver.refeicao_padrao(
        em_brasilia(TERCA, time(21, 0)), refeicoes(QUARTA, ALMOCO, JANTAR)
    )

    assert padrao == RefeicaoPadrao(refeicao=ALMOCO, dia=QUARTA, encerrada=False)


def test_dia_passado_mostra_a_ultima_refeicao_encerrada(resolver):
    padrao = resolver.refeicao_padrao(em_brasilia(QUARTA, time(8, 0)), TRES)

    assert padrao == RefeicaoPadrao(refeicao=JANTAR, dia=TERCA, encerrada=True)


def test_sem_refeicoes_no_dia_e_erro_de_quem_chamou(resolver):
    # Dia sem serviço é o item 5 da RN05, resolvido pelo CardapioQueryService
    # com o próximo dia com serviço, antes de chamar o resolver.
    with pytest.raises(ValueError):
        resolver.refeicao_padrao(em_brasilia(TERCA, time(12, 0)), [])


# --- Métodos auxiliares ------------------------------------------------------


@pytest.mark.parametrize(
    "hora, esperado",
    [
        (time(6, 59), None),
        (time(8, 0), CAFE),
        (time(10, 0), None),
        (time(14, 30), ALMOCO),
        (time(18, 0), JANTAR),
        (time(19, 31), None),
    ],
)
def test_refeicao_em_andamento(resolver, hora, esperado):
    assert resolver.refeicao_em_andamento(em_brasilia(TERCA, hora), TRES) == esperado


def test_refeicao_em_andamento_so_conta_refeicao_do_pdf(resolver):
    # Às 8h00 o café do Anexo A está no horário, mas o PDF não tem café.
    assert (
        resolver.refeicao_em_andamento(
            em_brasilia(TERCA, time(8, 0)), refeicoes(TERCA, ALMOCO)
        )
        is None
    )


@pytest.mark.parametrize(
    "hora, esperado",
    [
        (time(6, 59), CAFE),
        (time(8, 0), ALMOCO),
        (time(10, 0), ALMOCO),
        (time(15, 0), JANTAR),
        (time(17, 0), None),
        (time(20, 0), None),
    ],
)
def test_proxima_refeicao(resolver, hora, esperado):
    assert resolver.proxima_refeicao(em_brasilia(TERCA, hora), TRES) == esperado


def test_ultima_refeicao_do_dia(resolver):
    assert resolver.ultima_refeicao_do_dia(TRES) == JANTAR
    assert resolver.ultima_refeicao_do_dia(refeicoes(TERCA, CAFE, ALMOCO)) == ALMOCO
    assert resolver.ultima_refeicao_do_dia(refeicoes(TERCA, CAFE)) == CAFE


# --- Horários lidos da configuração (Anexo A) -------------------------------


def test_horarios_vem_do_horarios_refeicao_config(resolver, monkeypatch):
    # Se o Anexo A mudar o almoço para 11h30–15h00, o resolver acompanha sem
    # mudar código: 11h15 deixa de ser almoço em andamento, 14h45 passa a ser.
    monkeypatch.setattr(
        HorariosRefeicaoConfig, "horario_almoco", (time(11, 30), time(15, 0))
    )

    assert (
        resolver.refeicao_em_andamento(em_brasilia(TERCA, time(11, 15)), TRES) is None
    )
    assert (
        resolver.refeicao_em_andamento(em_brasilia(TERCA, time(14, 45)), TRES) == ALMOCO
    )


@pytest.mark.parametrize("tipo", [CAFE, ALMOCO, JANTAR])
def test_mesma_janela_do_checkin_da_fila(resolver, tipo):
    # Não pode haver um instante em que o check-in aceita uma refeição e o
    # cardápio já mostra outra como padrão (decisão de 21/11/2026).
    inicio, fim = JanelaCheckinValidator().janela(tipo)
    validador = JanelaCheckinValidator()
    um_segundo = timedelta(seconds=1)
    for instante in (
        em_brasilia(TERCA, inicio) - um_segundo,
        em_brasilia(TERCA, inicio),
        em_brasilia(TERCA, fim),
        em_brasilia(TERCA, fim) + um_segundo,
    ):
        no_checkin = validador.dentro_do_horario(tipo, instante)
        no_cardapio = resolver.refeicao_em_andamento(instante, TRES) == tipo
        assert no_cardapio == no_checkin, instante


def test_o_resolver_nao_le_o_relogio(resolver, monkeypatch):
    # Com o relógio quebrado, o resolver continua funcionando: só usa o
    # `agora` recebido.
    def relogio_proibido(*args, **kwargs):
        raise AssertionError("o resolver leu o relógio")

    monkeypatch.setattr("django.utils.timezone.now", relogio_proibido)

    padrao = resolver.refeicao_padrao(em_brasilia(TERCA, time(12, 0)), TRES)

    assert padrao.refeicao == ALMOCO


def test_refeicao_padrao_traz_o_dia_das_refeicoes(resolver):
    dia = date(2026, 12, 1)

    padrao = resolver.refeicao_padrao(
        em_brasilia(dia, time(12, 0)), refeicoes(dia, ALMOCO)
    )

    assert padrao.dia == dia
