"""CardapioQueryService: a orquestração do cardápio (BE-11, Exposição N4 4a).

Ordem (guia da BE-11, 5.2): resolve o dia e a refeição (RN05, com o próximo
dia com serviço), confere se a semana do dia exibido está publicada
(`FonteCardapio`), busca a refeição e aplica primeiro a dieta, depois os
marcadores. O `agora` vem de fora, como na view.

Os casos de domingo, refeição encerrada e virada de semana (sábado ->
domingo -> segunda) da tabela 9.2 do guia estão aqui, porque dependem do
banco. Os outros horários estão em test_horario_refeicao_resolver.py.
"""

import logging
from datetime import time, timedelta

import pytest

from apps.cardapio.cardapio_filtrado import (
    AVISO_SUJEITO_A_ALTERACAO,
    CardapioFiltrado,
    StatusCardapio,
)
from apps.cardapio.cardapio_query_service import CardapioQueryService, dia_pedido
from apps.cardapio.dieta_selecionada import DietaSelecionada
from apps.cardapio.horario_refeicao_resolver import refeicao_terminou
from apps.cardapio.models import Dieta, StatusLeitura, TipoRefeicao
from apps.cardapio.semana_cardapio_resolver import Semana
from apps.cardapio.tests.apoio_cardapio import (
    DOMINGO,
    PROXIMA_SEGUNDA,
    SABADO,
    SEGUNDA,
    TERCA,
    criar_campus,
    criar_categoria,
    criar_marcadores,
    criar_refeicao,
    em_brasilia,
    publicar_semana,
)

CAFE = TipoRefeicao.CAFE
ALMOCO = TipoRefeicao.ALMOCO
JANTAR = TipoRefeicao.JANTAR
QUARTA = TERCA + timedelta(days=1)
SEM_FILTRO = DietaSelecionada.SEM_FILTRO


@pytest.fixture
def campus(db):
    criar_marcadores()
    return criar_campus()


def servir(campus, dia, *tipos, status_leitura=StatusLeitura.OK):
    """Cria as refeições do dia, cada uma com um prato que diz qual é."""
    for tipo in tipos:
        refeicao = criar_refeicao(campus, dia, tipo, status_leitura)
        criar_categoria(refeicao, "Prato principal", 1, [(f"{tipo} {dia}", None, [])])


def obter(
    campus, agora, semana=None, dia=None, refeicao=None, marcadores=(), dieta=SEM_FILTRO
):
    return CardapioQueryService().obter_cardapio(
        campus, semana, dia, refeicao, list(marcadores), dieta, agora=agora
    )


def pratos(cardapio):
    return [p.descricao for c in cardapio.categorias for p in c.pratos]


# --- Publicado ---------------------------------------------------------------


def test_cardapio_publicado_da_refeicao_em_andamento(campus):
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, CAFE, ALMOCO, JANTAR)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert isinstance(cardapio, CardapioFiltrado)
    assert cardapio.campus == campus
    assert cardapio.status == StatusCardapio.PUBLICADO
    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, TERCA)
    assert cardapio.refeicao_encerrada is False
    assert cardapio.alergenos_indisponivel is False
    assert cardapio.filtro_marcador_desativado is False
    assert cardapio.sem_servico is False
    assert pratos(cardapio) == [f"almoco {TERCA}"]


def test_aviso_sujeito_a_alteracao_e_o_do_rf07_1(campus):
    # Texto decidido em 21/11/2026: o mesmo da CardapioView.vue.
    assert AVISO_SUJEITO_A_ALTERACAO == (
        "Cardápio sujeito a alteração. A ausência de marcador não garante que o "
        "prato esteja livre do ingrediente."
    )
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, ALMOCO)

    publicado = obter(campus, em_brasilia(TERCA, time(12, 0)))
    nao_publicado = obter(criar_campus("Ceilândia"), em_brasilia(TERCA, time(12, 0)))

    assert publicado.aviso_sujeito_a_alteracao == AVISO_SUJEITO_A_ALTERACAO
    assert nao_publicado.aviso_sujeito_a_alteracao == AVISO_SUJEITO_A_ALTERACAO


# --- Não publicado (RF07.3, RF18) --------------------------------------------


def test_refeicoes_sem_fonte_cardapio_ficam_nao_publicadas(campus):
    # Sem fallback pelas refeições (decisão de 21/11/2026).
    servir(campus, TERCA, CAFE, ALMOCO, JANTAR)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.categorias == []
    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, TERCA)
    assert cardapio.alergenos_indisponivel is False
    assert cardapio.filtro_marcador_desativado is False


@pytest.mark.parametrize(
    "hora, tipo, encerrada",
    [
        (time(6, 0), CAFE, False),
        (time(12, 0), ALMOCO, False),
        (time(20, 0), JANTAR, True),
    ],
)
def test_semana_sem_nada_no_banco_usa_os_horarios_do_anexo_a(
    campus, hora, tipo, encerrada
):
    cardapio = obter(campus, em_brasilia(TERCA, hora))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.sem_servico is False
    assert cardapio.categorias == []
    assert (cardapio.refeicao, cardapio.data, cardapio.refeicao_encerrada) == (
        tipo,
        TERCA,
        encerrada,
    )


def test_semana_publicada_de_outro_campus_nao_vale(campus):
    outro = criar_campus("Ceilândia")
    publicar_semana(outro, SEGUNDA)
    servir(campus, TERCA, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO


def test_semana_sem_linha_na_fonte_cardapio_fica_nao_publicada(campus):
    # A semana veio do resolver, mas a linha da FonteCardapio não existe:
    # quem decide o "publicado" é o existe_cardapio_publicado.
    class SemanaSemLinha:
        def semanas_disponiveis(self, campus, dia):
            return [Semana(inicio=SEGUNDA, fim=DOMINGO, vigente=True)]

    servir(campus, TERCA, ALMOCO)
    servico = CardapioQueryService()
    servico.semanas = SemanaSemLinha()

    cardapio = servico.obter_cardapio(
        campus, None, None, None, [], SEM_FILTRO, agora=em_brasilia(TERCA, time(12, 0))
    )

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.categorias == []


# --- Domingo e virada de semana (RN05, itens 3 a 5) --------------------------


@pytest.fixture
def duas_semanas(campus):
    """Sábado com almoço e jantar; domingo sem serviço; segunda seguinte com
    café e almoço. As duas semanas publicadas."""
    publicar_semana(campus, SEGUNDA)
    publicar_semana(campus, PROXIMA_SEGUNDA)
    servir(campus, SABADO, ALMOCO, JANTAR)
    servir(campus, PROXIMA_SEGUNDA, CAFE, ALMOCO)
    return campus


@pytest.mark.parametrize("hora", [time(0, 0), time(12, 0), time(23, 59)])
def test_domingo_mostra_a_primeira_refeicao_de_segunda(duas_semanas, hora):
    cardapio = obter(duas_semanas, em_brasilia(DOMINGO, hora))

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert (cardapio.refeicao, cardapio.data) == (CAFE, PROXIMA_SEGUNDA)
    assert cardapio.refeicao_encerrada is False
    assert pratos(cardapio) == [f"cafe {PROXIMA_SEGUNDA}"]


@pytest.mark.parametrize("hora", [time(20, 0), time(23, 59)])
def test_sabado_depois_do_jantar_mostra_o_jantar_encerrado(duas_semanas, hora):
    cardapio = obter(duas_semanas, em_brasilia(SABADO, hora))

    assert (cardapio.refeicao, cardapio.data) == (JANTAR, SABADO)
    assert cardapio.refeicao_encerrada is True
    assert cardapio.status == StatusCardapio.PUBLICADO


def test_virada_sabado_domingo_segunda(duas_semanas):
    sabado = obter(duas_semanas, em_brasilia(SABADO, time(23, 59)))
    domingo = obter(duas_semanas, em_brasilia(DOMINGO, time(0, 0)))
    segunda = obter(duas_semanas, em_brasilia(PROXIMA_SEGUNDA, time(10, 0)))

    assert (sabado.refeicao, sabado.data, sabado.refeicao_encerrada) == (
        JANTAR,
        SABADO,
        True,
    )
    assert (domingo.refeicao, domingo.data, domingo.refeicao_encerrada) == (
        CAFE,
        PROXIMA_SEGUNDA,
        False,
    )
    assert (segunda.refeicao, segunda.data, segunda.refeicao_encerrada) == (
        ALMOCO,
        PROXIMA_SEGUNDA,
        False,
    )


def test_domingo_com_a_segunda_de_semana_nao_publicada(campus):
    # Segunda já tem refeição no banco, mas o PDF da semana não foi lido
    # com sucesso: o dia exibido é segunda, e o cardápio, não publicado.
    publicar_semana(campus, SEGUNDA)
    servir(campus, SABADO, ALMOCO)
    servir(campus, PROXIMA_SEGUNDA, CAFE)

    cardapio = obter(campus, em_brasilia(DOMINGO, time(12, 0)))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert (cardapio.refeicao, cardapio.data) == (CAFE, PROXIMA_SEGUNDA)
    assert cardapio.categorias == []


def test_domingo_sem_nenhum_dia_com_servico_depois(campus):
    # Decisão do #217: o domingo está na semana de SEGUNDA (segunda a
    # domingo), que está publicada e não traz serviço nele. Então é "sem
    # serviço", como o sábado, e não "não publicado". A semana seguinte, que
    # ainda não saiu, aparece como não publicada quando a tela pedir a segunda.
    publicar_semana(campus, SEGUNDA)
    servir(campus, SABADO, ALMOCO)

    cardapio = obter(campus, em_brasilia(DOMINGO, time(12, 0)))

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.sem_servico is True
    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, DOMINGO)
    assert cardapio.categorias == []


# --- Sem serviço (#217, item 5) ----------------------------------------------


@pytest.fixture
def so_dias_uteis(campus):
    """Campus que só serve de segunda a sexta (campi 2 a 5), semana publicada."""
    publicar_semana(campus, SEGUNDA)
    for dias in range(5):
        servir(campus, SEGUNDA + timedelta(days=dias), CAFE, ALMOCO, JANTAR)
    return campus


@pytest.mark.parametrize(
    "hora, tipo, encerrada",
    [
        (time(6, 0), CAFE, False),
        (time(12, 0), ALMOCO, False),
        (time(20, 0), JANTAR, True),
    ],
)
def test_sabado_sem_servico_com_a_semana_publicada(
    so_dias_uteis, hora, tipo, encerrada
):
    # Aba "Sáb": o RU publicou a semana e não abre no sábado. A refeição vem
    # dos horários do Anexo A, e o dia exibido é o pedido.
    cardapio = obter(so_dias_uteis, em_brasilia(SABADO, hora))

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.sem_servico is True
    assert (cardapio.refeicao, cardapio.data, cardapio.refeicao_encerrada) == (
        tipo,
        SABADO,
        encerrada,
    )
    assert cardapio.categorias == []
    assert cardapio.alergenos_indisponivel is False
    assert cardapio.filtro_marcador_desativado is False


def test_sabado_pedido_de_outro_dia_sem_servico(so_dias_uteis):
    # A aba "Sáb" aberta na quarta: o dia pedido manda, não o de hoje.
    cardapio = obter(so_dias_uteis, em_brasilia(QUARTA, time(12, 0)), dia=SABADO)

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.sem_servico is True
    assert (cardapio.refeicao, cardapio.data) == (CAFE, SABADO)
    assert cardapio.refeicao_encerrada is False


def test_sabado_sem_servico_com_a_semana_nao_publicada(campus):
    # Sem a linha da FonteCardapio não dá para dizer que não há serviço: o RU
    # pode só não ter publicado ainda.
    for dias in range(5):
        servir(campus, SEGUNDA + timedelta(days=dias), ALMOCO)

    cardapio = obter(campus, em_brasilia(SABADO, time(12, 0)))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.sem_servico is False
    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, SABADO)
    assert cardapio.categorias == []


def test_sabado_sem_servico_com_so_a_semana_seguinte_publicada(campus):
    # A semana publicada tem que ser a do dia pedido, e não qualquer uma.
    publicar_semana(campus, PROXIMA_SEGUNDA)

    cardapio = obter(campus, em_brasilia(SABADO, time(12, 0)))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.sem_servico is False


def test_sabado_sem_servico_com_a_segunda_seguinte_servida(so_dias_uteis):
    # Com dia com serviço depois (RN05, item 5), vale o próximo dia, e não o
    # "sem serviço".
    publicar_semana(so_dias_uteis, PROXIMA_SEGUNDA)
    servir(so_dias_uteis, PROXIMA_SEGUNDA, CAFE)

    cardapio = obter(so_dias_uteis, em_brasilia(SABADO, time(12, 0)))

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.sem_servico is False
    assert (cardapio.refeicao, cardapio.data) == (CAFE, PROXIMA_SEGUNDA)


def test_refeicao_pedida_no_sabado_sem_servico_nao_e_sem_servico(so_dias_uteis):
    # Com `refeicao` no pedido, nada muda: "esta refeição não é servida".
    cardapio = obter(so_dias_uteis, em_brasilia(SABADO, time(12, 0)), refeicao=ALMOCO)

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.sem_servico is False
    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, SABADO)
    assert cardapio.categorias == []


def test_dia_util_sem_servico_vai_para_o_proximo_dia_com_servico(campus):
    # Ex.: feriado na terça. O PDF não traz refeição nesse dia.
    publicar_semana(campus, SEGUNDA)
    servir(campus, QUARTA, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, QUARTA)
    assert cardapio.status == StatusCardapio.PUBLICADO


# --- Dia, semana e refeição pedidos ------------------------------------------


def test_dia_futuro_pedido_mostra_a_primeira_refeicao(campus):
    publicar_semana(campus, SEGUNDA)
    servir(campus, QUARTA, CAFE, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(20, 0)), dia=QUARTA)

    assert (cardapio.refeicao, cardapio.data) == (CAFE, QUARTA)
    assert cardapio.refeicao_encerrada is False


def test_semana_pedida_sem_dia_e_fora_de_hoje_comeca_no_inicio(campus):
    # Quarta 25/11, pedindo a semana de 30/11: mostra a segunda 30/11, e não
    # o almoço de quarta (que também existe e está publicado).
    publicar_semana(campus, SEGUNDA)
    publicar_semana(campus, PROXIMA_SEGUNDA)
    servir(campus, QUARTA, ALMOCO)
    servir(campus, PROXIMA_SEGUNDA, ALMOCO)

    cardapio = obter(campus, em_brasilia(QUARTA, time(12, 0)), semana=PROXIMA_SEGUNDA)

    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, PROXIMA_SEGUNDA)
    assert pratos(cardapio) == [f"almoco {PROXIMA_SEGUNDA}"]


def test_semana_pedida_sem_dia_e_com_hoje_dentro_usa_hoje(campus):
    publicar_semana(campus, SEGUNDA)
    servir(campus, SEGUNDA, ALMOCO)
    servir(campus, TERCA, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)), semana=SEGUNDA)

    assert cardapio.data == TERCA


@pytest.mark.parametrize(
    "dia, hora, encerrada",
    [
        (TERCA, time(10, 0), False),  # ainda vai começar
        (TERCA, time(14, 30), False),  # fim incluído
        (TERCA, time(16, 0), True),  # já acabou hoje
        (QUARTA, time(16, 0), False),  # dia futuro
        (SEGUNDA, time(10, 0), True),  # dia passado
    ],
)
def test_refeicao_pedida_diz_se_ja_acabou(campus, dia, hora, encerrada):
    publicar_semana(campus, SEGUNDA)
    servir(campus, dia, CAFE, ALMOCO, JANTAR)

    cardapio = obter(campus, em_brasilia(TERCA, hora), dia=dia, refeicao=ALMOCO)

    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, dia)
    assert cardapio.refeicao_encerrada is encerrada
    assert pratos(cardapio) == [f"almoco {dia}"]


def test_refeicao_pedida_que_o_pdf_nao_traz_volta_sem_categorias(campus):
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(8, 0)), refeicao=CAFE)

    assert (cardapio.refeicao, cardapio.data) == (CAFE, TERCA)
    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.sem_servico is False
    assert cardapio.categorias == []


@pytest.mark.parametrize(
    "dia, hora, esperado",
    [
        (TERCA, time(14, 30), False),
        (TERCA, time(14, 31), True),
        (QUARTA, time(23, 0), False),
        (SEGUNDA, time(6, 0), True),
    ],
)
def test_refeicao_terminou(dia, hora, esperado):
    assert refeicao_terminou(em_brasilia(TERCA, hora), dia, ALMOCO) is esperado


# --- Filtros: primeiro a dieta, depois os marcadores -------------------------


@pytest.fixture
def almoco_completo(campus):
    publicar_semana(campus, SEGUNDA)
    refeicao = criar_refeicao(campus, TERCA, ALMOCO)
    criar_categoria(refeicao, "Salada", 1, [("Alface", None, [])])
    criar_categoria(
        refeicao, "Prato principal", 2, [("Frango xadrez", Dieta.PADRAO, ["soja"])]
    )
    criar_categoria(
        refeicao,
        "Prato principal vegetariano estrito",
        3,
        [("Tofu grelhado", Dieta.VEGETARIANO_ESTRITO, ["soja"])],
    )
    return refeicao


def test_dieta_e_marcador_combinados(campus, almoco_completo):
    cardapio = obter(
        campus,
        em_brasilia(TERCA, time(12, 0)),
        marcadores=["soja"],
        dieta=DietaSelecionada.VEGETARIANO_ESTRITO,
    )

    # A dieta tirou a linha padrão; o marcador sinalizou o que sobrou.
    assert [(c.nome, c.sem_opcao_compativel) for c in cardapio.categorias] == [
        ("Salada", False),
        ("Prato principal vegetariano estrito", True),
    ]
    tofu = cardapio.categorias[1].pratos[0]
    assert (tofu.descricao, tofu.contem_marcador_selecionado) == ("Tofu grelhado", True)


def test_sem_filtro_nao_remove_nada(campus, almoco_completo):
    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)), marcadores=["soja"])

    assert [c.nome for c in cardapio.categorias] == [
        "Salada",
        "Prato principal",
        "Prato principal vegetariano estrito",
    ]


@pytest.mark.parametrize("marcadores", [[], ["soja"]])
def test_alergenos_indisponiveis_desativam_o_filtro(campus, marcadores):
    publicar_semana(campus, SEGUNDA)
    refeicao = criar_refeicao(
        campus, TERCA, ALMOCO, StatusLeitura.ALERGENOS_INDISPONIVEIS
    )
    criar_categoria(refeicao, "Prato principal", 1, [("Tofu", None, ["soja"])])

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)), marcadores=marcadores)

    assert cardapio.alergenos_indisponivel is True
    assert cardapio.filtro_marcador_desativado is True
    [categoria] = cardapio.categorias
    assert categoria.sem_opcao_compativel is False
    assert categoria.pratos[0].contem_marcador_selecionado is False
    # O marcador continua listado no prato (RF10).
    assert categoria.pratos[0].marcadores == ["soja"]


# --- Revisão do PR #214 ------------------------------------------------------


def test_refeicao_com_leitura_falhou_fica_nao_publicada(campus):
    # `leitura_falhou` só existe numa linha criada sem cardápio anterior
    # (N4 do banco): não há cardápio válido para mostrar (RF06.4, RF07.3).
    # Publicá-la com o filtro de marcador ativo faria quem filtra glúten
    # achar que nada tem glúten.
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, ALMOCO, status_leitura=StatusLeitura.LEITURA_FALHOU)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)), marcadores=["soja"])

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.categorias == []
    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, TERCA)


def test_leitura_falhou_numa_refeicao_nao_afeta_as_outras(campus):
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, CAFE, status_leitura=StatusLeitura.LEITURA_FALHOU)
    servir(campus, TERCA, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert cardapio.status == StatusCardapio.PUBLICADO
    assert pratos(cardapio) == [f"almoco {TERCA}"]


def test_domingo_com_semana_pedida_pula_para_a_semana_seguinte(duas_semanas):
    # RN05, item 5: mesmo com `semana` pedida, o dia exibido é o próximo dia
    # com serviço, ainda que seja de outra semana; `data` mostra qual é.
    cardapio = obter(duas_semanas, em_brasilia(DOMINGO, time(12, 0)), semana=SEGUNDA)

    assert (cardapio.refeicao, cardapio.data) == (CAFE, PROXIMA_SEGUNDA)
    assert cardapio.status == StatusCardapio.PUBLICADO


def test_proximo_dia_com_servico_a_mais_de_uma_semana_nao_conta(campus):
    # A busca vai até 7 dias depois: num recesso longo, a tela fica no dia
    # pedido, em vez de mostrar uma refeição de semanas à frente. Com a semana
    # publicada, é "sem serviço" (#217); antes, saía "não publicado".
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA + timedelta(days=8), ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert (cardapio.status, cardapio.sem_servico) == (StatusCardapio.PUBLICADO, True)
    assert cardapio.data == TERCA
    assert cardapio.categorias == []


def test_recesso_longo_com_a_semana_nao_publicada(campus):
    servir(campus, TERCA + timedelta(days=8), ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert (cardapio.status, cardapio.sem_servico) == (
        StatusCardapio.NAO_PUBLICADO,
        False,
    )
    assert cardapio.data == TERCA


def test_refeicao_pedida_no_domingo_nao_pula_de_dia(duas_semanas):
    # O item 5 da RN05 vale para a refeição padrão. Pedida pelo seletor, a
    # refeição é a do dia pedido: o PDF não a traz, e as categorias vêm
    # vazias (o front só oferece os dias e refeições do PDF).
    cardapio = obter(
        duas_semanas, em_brasilia(SABADO, time(12, 0)), dia=DOMINGO, refeicao=ALMOCO
    )

    assert (cardapio.refeicao, cardapio.data) == (ALMOCO, DOMINGO)
    assert cardapio.status == StatusCardapio.PUBLICADO
    assert cardapio.categorias == []


def test_refeicao_pedida_em_semana_nao_publicada(campus):
    servir(campus, TERCA, ALMOCO)

    cardapio = obter(campus, em_brasilia(TERCA, time(16, 0)), refeicao=ALMOCO)

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert (cardapio.refeicao, cardapio.data, cardapio.refeicao_encerrada) == (
        ALMOCO,
        TERCA,
        True,
    )
    assert cardapio.categorias == []


def test_agora_em_utc_no_servico_usa_o_dia_de_brasilia(campus):
    # 01h00 UTC de quarta = 22h00 de terça em Brasília: jantar de terça.
    from datetime import UTC, datetime

    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, ALMOCO, JANTAR)
    servir(campus, QUARTA, CAFE)

    cardapio = obter(campus, datetime(2026, 11, 25, 1, 0, tzinfo=UTC))

    assert (cardapio.refeicao, cardapio.data, cardapio.refeicao_encerrada) == (
        JANTAR,
        TERCA,
        True,
    )


def test_refeicao_terminou_com_agora_em_utc():
    from datetime import UTC, datetime

    # 17h31 UTC = 14h31 em Brasília: o almoço de terça acabou.
    assert refeicao_terminou(datetime(2026, 11, 24, 17, 31, tzinfo=UTC), TERCA, ALMOCO)
    # 17h30 UTC = 14h30: ainda no horário (fim incluído).
    assert not refeicao_terminou(
        datetime(2026, 11, 24, 17, 30, tzinfo=UTC), TERCA, ALMOCO
    )


@pytest.mark.parametrize(
    "hoje, esperado",
    [
        (SEGUNDA - timedelta(days=1), SEGUNDA),  # antes da semana
        (SEGUNDA, SEGUNDA),  # primeiro dia: hoje
        (DOMINGO, DOMINGO),  # último dia: hoje
        (PROXIMA_SEGUNDA, SEGUNDA),  # depois da semana
    ],
)
def test_dia_pedido_com_semana_e_sem_dia(hoje, esperado):
    assert dia_pedido(SEGUNDA, None, hoje) == esperado


def test_dia_pedido_sem_semana_e_hoje_e_com_dia_e_o_dia():
    assert dia_pedido(None, None, TERCA) == TERCA
    assert dia_pedido(SEGUNDA, QUARTA, TERCA) == QUARTA


# --- Logs de configuração (revisão do PR #214, item 9) -----------------------

LOGGER_SERVICO = "apps.cardapio.cardapio_query_service"


def test_refeicao_sem_fonte_cardapio_deixa_aviso_no_log(campus, caplog):
    # Ex.: cardápio cadastrado à mão sem a linha da semana (plano B da BE-12).
    servir(campus, TERCA, ALMOCO)

    with caplog.at_level(logging.WARNING, logger=LOGGER_SERVICO):
        obter(campus, em_brasilia(TERCA, time(12, 0)))

    [registro] = caplog.records
    assert registro.levelno == logging.WARNING
    assert "FonteCardapio" in registro.getMessage()
    assert str(campus.pk) in registro.getMessage()
    assert TERCA.isoformat() in registro.getMessage()


def test_semana_sem_nada_no_banco_nao_vai_para_o_log(campus, caplog):
    # Segunda de manhã, antes de o PDF sair: situação normal, sem aviso.
    with caplog.at_level(logging.DEBUG, logger=LOGGER_SERVICO):
        obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert caplog.records == []


def test_cardapio_publicado_nao_vai_para_o_log(campus, caplog):
    publicar_semana(campus, SEGUNDA)
    servir(campus, TERCA, ALMOCO)

    with caplog.at_level(logging.DEBUG, logger=LOGGER_SERVICO):
        obter(campus, em_brasilia(TERCA, time(12, 0)))

    assert caplog.records == []


def test_refeicao_pedida_sem_nada_no_banco_nao_vai_para_o_log(campus, caplog):
    with caplog.at_level(logging.DEBUG, logger=LOGGER_SERVICO):
        obter(campus, em_brasilia(TERCA, time(12, 0)), refeicao=ALMOCO)

    assert caplog.records == []
