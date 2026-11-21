"""CardapioQueryService: a orquestração do cardápio (BE-11, Exposição N4 4a).

Ordem (guia da BE-11, 5.2): resolve o dia e a refeição (RN05, com o próximo
dia com serviço), confere se a semana do dia exibido está publicada
(`FonteCardapio`), busca a refeição e aplica primeiro a dieta, depois os
marcadores. O `agora` vem de fora, como na view.

Os casos de domingo, refeição encerrada e virada de semana (sábado ->
domingo -> segunda) da tabela 9.2 do guia estão aqui, porque dependem do
banco. Os outros horários estão em test_horario_refeicao_resolver.py.
"""

from datetime import time, timedelta

import pytest

from apps.cardapio.cardapio_filtrado import (
    AVISO_SUJEITO_A_ALTERACAO,
    CardapioFiltrado,
    StatusCardapio,
)
from apps.cardapio.cardapio_query_service import CardapioQueryService
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
    publicar_semana(campus, SEGUNDA)
    servir(campus, SABADO, ALMOCO)

    cardapio = obter(campus, em_brasilia(DOMINGO, time(12, 0)))

    assert cardapio.status == StatusCardapio.NAO_PUBLICADO
    assert cardapio.data == DOMINGO
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
