"""FiltroMarcadorService (BE-11, RF08, RF10, Exposição N4 4a).

Critérios do RF08 que estes testes seguem:
- os pratos com marcador selecionado continuam visíveis e são sinalizados
  ("Contém: leite e derivados");
- a categoria em que todos os pratos têm marcador selecionado exibe "sem
  opção compatível" (e continua na resposta);
- com "informação de alérgenos indisponível" (RF06.3) o filtro fica
  desativado: nada é sinalizado.
RF10: `marcadores` traz sempre todos os marcadores do prato, com ou sem filtro.
"""

import pytest

from apps.cardapio.cardapio_filtrado import CategoriaFiltrada, PratoFiltrado
from apps.cardapio.filtro_marcador_service import FiltroMarcadorService
from apps.cardapio.models import Categoria
from apps.cardapio.tests.apoio_cardapio import (
    TERCA,
    criar_campus,
    criar_categoria,
    criar_marcadores,
    criar_refeicao,
)


@pytest.fixture
def refeicao(db):
    criar_marcadores()
    return criar_refeicao(criar_campus(), TERCA)


@pytest.fixture
def principal(refeicao):
    """Uma categoria com um prato com leite e outro sem."""
    return criar_categoria(
        refeicao,
        "Prato principal",
        1,
        [
            ("Strogonoff", None, ["leite_e_derivados", "pimenta"]),
            ("Frango assado", None, ["pimenta"]),
        ],
    )


@pytest.fixture
def sobremesa(refeicao):
    """Uma categoria em que todos os pratos têm leite."""
    return criar_categoria(
        refeicao,
        "Sobremesa",
        2,
        [
            ("Pudim", None, ["leite_e_derivados", "ovo"]),
            ("Doce de leite", None, ["leite_e_derivados"]),
        ],
    )


def aplicar(categorias, marcadores=(), alergenos_indisponivel=False):
    return FiltroMarcadorService().aplicar(
        categorias, list(marcadores), alergenos_indisponivel
    )


def por_descricao(categoria_filtrada):
    return {p.descricao: p for p in categoria_filtrada.pratos}


def test_prato_com_marcador_selecionado_continua_e_e_sinalizado(principal):
    [categoria] = aplicar([principal], ["leite_e_derivados"])

    pratos = por_descricao(categoria)
    assert set(pratos) == {"Strogonoff", "Frango assado"}
    assert pratos["Strogonoff"].contem_marcador_selecionado is True
    assert pratos["Frango assado"].contem_marcador_selecionado is False


def test_basta_um_dos_marcadores_selecionados(principal):
    [categoria] = aplicar([principal], ["soja", "leite_e_derivados"])

    assert por_descricao(categoria)["Strogonoff"].contem_marcador_selecionado is True
    assert (
        por_descricao(categoria)["Frango assado"].contem_marcador_selecionado is False
    )


def test_marcador_que_o_prato_nao_tem_nao_sinaliza(principal):
    [categoria] = aplicar([principal], ["soja"])

    assert [p.contem_marcador_selecionado for p in categoria.pratos] == [False, False]


def test_categoria_com_todos_os_pratos_marcados_fica_sem_opcao_compativel(
    principal, sobremesa
):
    resultado = aplicar([principal, sobremesa], ["leite_e_derivados"])

    assert [(c.nome, c.sem_opcao_compativel) for c in resultado] == [
        ("Prato principal", False),
        ("Sobremesa", True),
    ]
    # A categoria continua na resposta, com os pratos (RF08).
    assert [p.descricao for p in resultado[1].pratos] == ["Pudim", "Doce de leite"]


def test_marcadores_diferentes_em_cada_prato_tambem_deixam_sem_opcao(sobremesa):
    # Pudim tem ovo; doce de leite, leite: cada prato tem um dos selecionados.
    [categoria] = aplicar([sobremesa], ["ovo"])
    assert categoria.sem_opcao_compativel is False

    [categoria] = aplicar([sobremesa], ["ovo", "leite_e_derivados"])
    assert categoria.sem_opcao_compativel is True


def test_um_prato_livre_basta_para_ter_opcao(principal):
    [categoria] = aplicar([principal], ["leite_e_derivados"])

    assert categoria.sem_opcao_compativel is False


def test_sem_marcador_selecionado_nada_e_sinalizado(principal, sobremesa):
    resultado = aplicar([principal, sobremesa])

    assert [c.sem_opcao_compativel for c in resultado] == [False, False]
    assert all(not p.contem_marcador_selecionado for c in resultado for p in c.pratos)


def test_marcadores_do_prato_saem_sempre_completos(principal):
    # RF10: com filtro, sem filtro e com o filtro desativado.
    for selecionados, indisponivel in [
        ([], False),
        (["leite_e_derivados"], False),
        (["leite_e_derivados"], True),
    ]:
        [categoria] = aplicar([principal], selecionados, indisponivel)
        pratos = por_descricao(categoria)
        assert pratos["Strogonoff"].marcadores == ["leite_e_derivados", "pimenta"]
        assert pratos["Frango assado"].marcadores == ["pimenta"]


def test_marcadores_saem_na_ordem_da_fixture(refeicao):
    # Ordem fixa (id do marcador), para a resposta não mudar de uma consulta
    # para outra.
    categoria = criar_categoria(
        refeicao, "Pão", 1, [("Pão de mel", None, ["trigo_gluten", "mel", "ovo"])]
    )

    [filtrada] = aplicar([categoria])

    assert filtrada.pratos[0].marcadores == ["mel", "trigo_gluten", "ovo"]


def test_alergenos_indisponiveis_desativam_toda_sinalizacao(principal, sobremesa):
    resultado = aplicar(
        [principal, sobremesa], ["leite_e_derivados"], alergenos_indisponivel=True
    )

    assert [c.sem_opcao_compativel for c in resultado] == [False, False]
    assert [p.contem_marcador_selecionado for c in resultado for p in c.pratos] == [
        False,
        False,
        False,
        False,
    ]


def test_categoria_vazia_nao_fica_sem_opcao_compativel(refeicao):
    vazia = criar_categoria(refeicao, "Sopa", 1)

    [categoria] = aplicar([vazia], ["leite_e_derivados"])

    assert categoria.pratos == []
    assert categoria.sem_opcao_compativel is False


def test_mantem_a_ordem_das_categorias_e_a_dos_pratos_do_pdf(refeicao):
    segunda = criar_categoria(refeicao, "Guarnição", 2, [("Arroz", None, [])])
    primeira = criar_categoria(
        refeicao,
        "Salada",
        1,
        [("Alface", None, []), ("Tomate", None, []), ("Cenoura", None, [])],
    )
    # Inverte a ordem dos pratos no banco: a resposta segue `Prato.ordem`.
    for prato, ordem in zip(primeira.pratos.order_by("ordem"), (3, 1, 2), strict=True):
        prato.ordem = ordem
        prato.save()

    resultado = aplicar([primeira, segunda])

    assert [c.nome for c in resultado] == ["Salada", "Guarnição"]
    assert [p.descricao for p in resultado[0].pratos] == [
        "Tomate",
        "Cenoura",
        "Alface",
    ]


def test_produz_categoria_filtrada_e_prato_filtrado(principal):
    [categoria] = aplicar([principal], ["leite_e_derivados"])

    assert categoria == CategoriaFiltrada(
        nome="Prato principal",
        sem_opcao_compativel=False,
        pratos=[
            PratoFiltrado(
                descricao="Strogonoff",
                marcadores=["leite_e_derivados", "pimenta"],
                contem_marcador_selecionado=True,
            ),
            PratoFiltrado(
                descricao="Frango assado",
                marcadores=["pimenta"],
                contem_marcador_selecionado=False,
            ),
        ],
    )


def test_nao_escreve_no_banco(principal):
    # A Exposição só lê os models (quem escreve é o Leitor).
    antes = list(Categoria.objects.values_list("id", "nome", "ordem"))

    aplicar([principal], ["leite_e_derivados"])

    assert list(Categoria.objects.values_list("id", "nome", "ordem")) == antes
