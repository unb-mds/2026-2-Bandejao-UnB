"""FiltroDietaService e DietaSelecionada (BE-11, RF09, Exposição N4 4a).

A dieta fica no prato, e todos os pratos de uma categoria têm a mesma dieta.
O serviço mantém ou remove a categoria inteira (tabela 5.7 do guia da BE-11):

| Dieta escolhida      | Mantém categorias de dieta...            | Remove             |
| sem_filtro           | todas (inclusive categoria vazia)        | nada               |
| ovolactovegetariano  | ovolacto, vegetariano_estrito ou nula    | padrao             |
| vegetariano_estrito  | vegetariano_estrito ou nula              | padrao, ovolacto   |

Os valores esperados saem do RF09: "Dado Ovolactovegetariano, aparecem as
linhas ovolactovegetariana e vegetariana estrita e a linha padrão é
ocultada; com Vegetariano estrito, aparece só a linha vegetariana estrita",
e "as demais categorias (saladas, guarnição, sopa etc.) continuam visíveis".
"""

import pytest

from apps.cardapio.dieta_selecionada import DietaSelecionada
from apps.cardapio.filtro_dieta_service import FiltroDietaService
from apps.cardapio.models import Dieta
from apps.cardapio.tests.apoio_cardapio import (
    TERCA,
    criar_campus,
    criar_categoria,
    criar_marcadores,
    criar_refeicao,
)

SALADA = "Salada"
PADRAO = "Prato principal"
OVOLACTO = "Prato principal ovolactovegetariano"
ESTRITO = "Prato principal vegetariano estrito"
GUARNICAO = "Guarnição"
SOPA_VAZIA = "Sopa"


@pytest.fixture
def almoco(db):
    """Almoço com as três linhas de dieta, duas categorias comuns e uma vazia.

    As categorias são criadas fora da ordem do PDF de propósito.
    """
    criar_marcadores()
    refeicao = criar_refeicao(criar_campus(), TERCA)
    criar_categoria(refeicao, GUARNICAO, 5, [("Arroz", None, []), ("Feijão", None, [])])
    criar_categoria(refeicao, PADRAO, 2, [("Frango assado", Dieta.PADRAO, [])])
    criar_categoria(refeicao, SALADA, 1, [("Alface", None, [])])
    criar_categoria(
        refeicao, ESTRITO, 4, [("Tofu grelhado", Dieta.VEGETARIANO_ESTRITO, ["soja"])]
    )
    criar_categoria(refeicao, OVOLACTO, 3, [("Omelete", Dieta.OVOLACTO, ["ovo"])])
    criar_categoria(refeicao, SOPA_VAZIA, 6)
    return refeicao


def nomes(categorias):
    return [categoria.nome for categoria in categorias]


def test_dieta_selecionada_tem_os_valores_do_contrato():
    # Os valores são os do parâmetro `dieta` no openapi.yaml.
    assert [d.value for d in DietaSelecionada] == [
        "sem_filtro",
        "ovolactovegetariano",
        "vegetariano_estrito",
    ]
    assert DietaSelecionada.SEM_FILTRO == "sem_filtro"
    assert DietaSelecionada.OVOLACTOVEGETARIANO == "ovolactovegetariano"
    assert DietaSelecionada.VEGETARIANO_ESTRITO == "vegetariano_estrito"


def test_dieta_selecionada_nao_e_o_enum_dieta_do_prato():
    # `Dieta` é a do prato (padrao, ovolacto...); a escolhida pelo usuário é
    # outra coisa, com outros valores.
    assert "ovolacto" not in {d.value for d in DietaSelecionada}
    assert "padrao" not in {d.value for d in DietaSelecionada}


def test_sem_filtro_mantem_todas_as_categorias_na_ordem_do_pdf(almoco):
    categorias = FiltroDietaService().aplicar(almoco, DietaSelecionada.SEM_FILTRO)

    assert nomes(categorias) == [
        SALADA,
        PADRAO,
        OVOLACTO,
        ESTRITO,
        GUARNICAO,
        SOPA_VAZIA,
    ]


def test_sem_filtro_mantem_a_categoria_vazia(almoco):
    categorias = FiltroDietaService().aplicar(almoco, DietaSelecionada.SEM_FILTRO)

    vazia = [c for c in categorias if c.nome == SOPA_VAZIA]
    assert len(vazia) == 1
    assert list(vazia[0].pratos.all()) == []


def test_ovolacto_mostra_ovolacto_e_estrita_e_esconde_a_padrao(almoco):
    categorias = FiltroDietaService().aplicar(
        almoco, DietaSelecionada.OVOLACTOVEGETARIANO
    )

    assert nomes(categorias) == [SALADA, OVOLACTO, ESTRITO, GUARNICAO, SOPA_VAZIA]
    assert PADRAO not in nomes(categorias)


def test_vegetariano_estrito_mostra_so_a_linha_estrita(almoco):
    categorias = FiltroDietaService().aplicar(
        almoco, DietaSelecionada.VEGETARIANO_ESTRITO
    )

    assert nomes(categorias) == [SALADA, ESTRITO, GUARNICAO, SOPA_VAZIA]
    assert PADRAO not in nomes(categorias)
    assert OVOLACTO not in nomes(categorias)


@pytest.mark.parametrize("dieta", list(DietaSelecionada))
def test_categorias_de_dieta_nula_ficam_em_qualquer_dieta(almoco, dieta):
    categorias = FiltroDietaService().aplicar(almoco, dieta)

    assert {SALADA, GUARNICAO, SOPA_VAZIA} <= set(nomes(categorias))


def test_devolve_as_proprias_categorias_do_model(almoco):
    # A saída alimenta o FiltroMarcadorService, que lê os pratos de cada uma.
    categorias = FiltroDietaService().aplicar(
        almoco, DietaSelecionada.VEGETARIANO_ESTRITO
    )

    esperadas = almoco.categorias.filter(
        nome__in=[SALADA, ESTRITO, GUARNICAO, SOPA_VAZIA]
    )
    assert {c.pk for c in categorias} == {c.pk for c in esperadas}


def test_categoria_com_um_prato_de_dieta_proibida_sai(db):
    # Pelo Leitor, isso não acontece (todos os pratos da categoria têm a
    # mesma dieta). Se acontecer, a categoria sai: mostrar a linha a quem
    # é vegetariano estrito com um prato que ele não come seria o erro pior.
    criar_marcadores()
    refeicao = criar_refeicao(criar_campus(), TERCA)
    criar_categoria(
        refeicao,
        ESTRITO,
        1,
        [
            ("Tofu", Dieta.VEGETARIANO_ESTRITO, []),
            ("Omelete", Dieta.OVOLACTO, []),
        ],
    )

    categorias = FiltroDietaService().aplicar(
        refeicao, DietaSelecionada.VEGETARIANO_ESTRITO
    )

    assert categorias == []
