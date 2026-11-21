"""RefeicaoRepository: leitura das refeições do cardápio (BE-11, Exposição N4 4a).

Só leitura: quem escreve nos models é o Leitor (BE-12). A refeição vem com
categorias, pratos e marcadores já carregados, para não haver uma consulta
por prato (RNF01).
"""

from datetime import timedelta

import pytest

from apps.cardapio.models import TipoRefeicao
from apps.cardapio.refeicao_repository import RefeicaoRepository
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
    publicar_semana,
)

CAFE = TipoRefeicao.CAFE
ALMOCO = TipoRefeicao.ALMOCO
JANTAR = TipoRefeicao.JANTAR


@pytest.fixture
def campus(db):
    criar_marcadores()
    return criar_campus()


@pytest.fixture
def repositorio():
    return RefeicaoRepository()


# --- buscar_refeicao ---------------------------------------------------------


def test_buscar_refeicao_acha_pelo_campus_data_e_tipo(campus, repositorio):
    almoco = criar_refeicao(campus, TERCA, ALMOCO)
    criar_refeicao(campus, TERCA, JANTAR)
    criar_refeicao(campus, SEGUNDA, ALMOCO)
    criar_refeicao(criar_campus("Ceilândia"), TERCA, ALMOCO)

    assert repositorio.buscar_refeicao(campus, TERCA, ALMOCO).pk == almoco.pk


def test_buscar_refeicao_inexistente_devolve_none(campus, repositorio):
    criar_refeicao(campus, TERCA, ALMOCO)

    assert repositorio.buscar_refeicao(campus, TERCA, CAFE) is None
    assert repositorio.buscar_refeicao(campus, SEGUNDA, ALMOCO) is None


def test_buscar_refeicao_traz_tudo_em_quatro_consultas(
    campus, repositorio, django_assert_num_queries
):
    refeicao = criar_refeicao(campus, TERCA, ALMOCO)
    for ordem in range(1, 6):
        criar_categoria(
            refeicao,
            f"Categoria {ordem}",
            ordem,
            [(f"Prato {ordem}.{n}", None, ["ovo", "soja"]) for n in range(4)],
        )

    # Refeição, categorias, pratos e marcadores: uma consulta cada.
    with django_assert_num_queries(4):
        encontrada = repositorio.buscar_refeicao(campus, TERCA, ALMOCO)
    # Percorrer tudo depois não consulta mais o banco.
    with django_assert_num_queries(0):
        marcadores = [
            m.nome
            for c in encontrada.categorias.all()
            for p in c.pratos.all()
            for m in p.marcadores.all()
        ]
    assert len(marcadores) == 5 * 4 * 2


def test_buscar_refeicao_traz_categorias_e_pratos_na_ordem_do_pdf(campus, repositorio):
    refeicao = criar_refeicao(campus, TERCA, ALMOCO)
    criar_categoria(refeicao, "Guarnição", 2, [("Arroz", None, [])])
    criar_categoria(refeicao, "Salada", 1, [("Alface", None, []), ("Tomate", None, [])])

    encontrada = repositorio.buscar_refeicao(campus, TERCA, ALMOCO)

    categorias = list(encontrada.categorias.all())
    assert [c.nome for c in categorias] == ["Salada", "Guarnição"]
    assert [p.nome for p in categorias[0].pratos.all()] == ["Alface", "Tomate"]


# --- refeicoes_do_dia --------------------------------------------------------


def test_refeicoes_do_dia_na_ordem_cafe_almoco_jantar(campus, repositorio):
    # Criadas fora de ordem: a ordem é a do dia (Anexo A), não a de criação.
    criar_refeicao(campus, TERCA, JANTAR)
    criar_refeicao(campus, TERCA, CAFE)
    criar_refeicao(campus, TERCA, ALMOCO)

    tipos = [r.tipo for r in repositorio.refeicoes_do_dia(campus, TERCA)]

    assert tipos == [CAFE, ALMOCO, JANTAR]


def test_refeicoes_do_dia_so_do_campus_e_do_dia(campus, repositorio):
    criar_refeicao(campus, TERCA, ALMOCO)
    criar_refeicao(campus, SEGUNDA, CAFE)
    criar_refeicao(criar_campus("Ceilândia"), TERCA, JANTAR)

    refeicoes = repositorio.refeicoes_do_dia(campus, TERCA)

    assert [(r.campus_id, r.data, r.tipo) for r in refeicoes] == [
        (campus.pk, TERCA, ALMOCO)
    ]


def test_refeicoes_do_dia_sem_servico_devolve_lista_vazia(campus, repositorio):
    criar_refeicao(campus, SABADO, ALMOCO)

    assert repositorio.refeicoes_do_dia(campus, DOMINGO) == []


# --- proximo_dia_com_servico -------------------------------------------------


def test_proximo_dia_com_servico_pula_o_domingo(campus, repositorio):
    criar_refeicao(campus, SABADO, ALMOCO)
    criar_refeicao(campus, PROXIMA_SEGUNDA, CAFE)
    criar_refeicao(campus, PROXIMA_SEGUNDA + timedelta(days=1), CAFE)

    assert repositorio.proximo_dia_com_servico(campus, SABADO) == PROXIMA_SEGUNDA
    assert repositorio.proximo_dia_com_servico(campus, DOMINGO) == PROXIMA_SEGUNDA


def test_proximo_dia_com_servico_e_estritamente_depois(campus, repositorio):
    criar_refeicao(campus, TERCA, ALMOCO)
    criar_refeicao(campus, TERCA + timedelta(days=1), ALMOCO)

    assert repositorio.proximo_dia_com_servico(campus, TERCA) == TERCA + timedelta(
        days=1
    )


def test_proximo_dia_com_servico_ignora_outro_campus(campus, repositorio):
    criar_refeicao(criar_campus("Ceilândia"), PROXIMA_SEGUNDA, ALMOCO)

    assert repositorio.proximo_dia_com_servico(campus, DOMINGO) is None


def test_sem_proximo_dia_com_servico_devolve_none(campus, repositorio):
    criar_refeicao(campus, SABADO, ALMOCO)

    assert repositorio.proximo_dia_com_servico(campus, SABADO) is None


# --- existe_cardapio_publicado -----------------------------------------------


def test_existe_cardapio_publicado_com_a_linha_da_semana(campus, repositorio):
    publicar_semana(campus, SEGUNDA)

    assert repositorio.existe_cardapio_publicado(
        campus, Semana(inicio=SEGUNDA, fim=DOMINGO, vigente=True)
    )


def test_sem_a_linha_da_semana_nao_esta_publicado(campus, repositorio):
    # Mesmo com refeição no banco (sem fallback pelas refeições).
    criar_refeicao(campus, TERCA, ALMOCO)
    publicar_semana(campus, PROXIMA_SEGUNDA)
    publicar_semana(criar_campus("Ceilândia"), SEGUNDA)

    assert not repositorio.existe_cardapio_publicado(
        campus, Semana(inicio=SEGUNDA, fim=DOMINGO, vigente=True)
    )


def test_repositorio_nao_escreve_no_banco(campus, repositorio):
    refeicao = criar_refeicao(campus, TERCA, ALMOCO)
    lida_em = refeicao.lida_em
    publicar_semana(campus, SEGUNDA)

    repositorio.buscar_refeicao(campus, TERCA, ALMOCO)
    repositorio.refeicoes_do_dia(campus, TERCA)
    repositorio.proximo_dia_com_servico(campus, TERCA)
    repositorio.existe_cardapio_publicado(
        campus, Semana(inicio=SEGUNDA, fim=DOMINGO, vigente=True)
    )

    # `lida_em` é auto_now: qualquer save() da Exposição mudaria o valor.
    refeicao.refresh_from_db()
    assert refeicao.lida_em == lida_em


def test_proximo_dia_com_servico_busca_ate_sete_dias(campus, repositorio):
    criar_refeicao(campus, TERCA + timedelta(days=7), ALMOCO)
    assert repositorio.proximo_dia_com_servico(campus, TERCA) == TERCA + timedelta(
        days=7
    )


def test_proximo_dia_com_servico_depois_de_sete_dias_e_none(campus, repositorio):
    criar_refeicao(campus, TERCA + timedelta(days=8), ALMOCO)
    assert repositorio.proximo_dia_com_servico(campus, TERCA) is None
