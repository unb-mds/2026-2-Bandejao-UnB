"""GET /api/cardapio/ (BE-11, #138, RF05, RF07, RF08, RF09, RN05, ADR 0005).

Integração com o APIClient do DRF: validação dos parâmetros (400
`parametros_invalidos` no formato `{codigo, mensagem}`), resposta igual ao
`CardapioFiltradoSerializer` e o relógio lido uma vez, na view. O relógio é
simulado com `unittest.mock.patch` em `django.utils.timezone.now`.
"""

from datetime import time
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.cardapio.cardapio_filtrado import AVISO_SUJEITO_A_ALTERACAO
from apps.cardapio.models import Dieta, StatusLeitura, TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import (
    DOMINGO,
    PROXIMA_SEGUNDA,
    SEGUNDA,
    TERCA,
    criar_campus,
    criar_categoria,
    criar_marcadores,
    criar_refeicao,
    em_brasilia,
    publicar_semana,
)

ROTA = "/api/cardapio/"
CHAVES_DO_CONTRATO = {
    "campus",
    "refeicao",
    "data",
    "refeicaoEncerrada",
    "status",
    "avisoSujeitoAAlteracao",
    "alergenosIndisponivel",
    "filtroMarcadorDesativado",
    "categorias",
}


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def campus(db):
    criar_marcadores()
    return criar_campus()


@pytest.fixture
def almoco(campus):
    """Almoço de terça 24/11 publicado, com as três linhas de dieta."""
    publicar_semana(campus, SEGUNDA)
    criar_refeicao(campus, TERCA, TipoRefeicao.CAFE)
    refeicao = criar_refeicao(campus, TERCA, TipoRefeicao.ALMOCO)
    criar_refeicao(campus, TERCA, TipoRefeicao.JANTAR)
    criar_categoria(refeicao, "Salada", 1, [("Alface", None, [])])
    criar_categoria(
        refeicao,
        "Prato principal",
        2,
        [("Frango assado", Dieta.PADRAO, ["pimenta"])],
    )
    criar_categoria(
        refeicao,
        "Prato principal ovolactovegetariano",
        3,
        [("Omelete", Dieta.OVOLACTO, ["ovo", "leite_e_derivados"])],
    )
    criar_categoria(
        refeicao,
        "Prato principal vegetariano estrito",
        4,
        [("Tofu grelhado", Dieta.VEGETARIANO_ESTRITO, ["soja"])],
    )
    return refeicao


def relogio(dia, hora):
    """Congela o `timezone.now()` no `dia` e `hora` de Brasília."""
    return mock.patch("django.utils.timezone.now", return_value=em_brasilia(dia, hora))


def pedir(cliente, agora=(TERCA, time(12, 0)), **parametros):
    with relogio(*agora):
        return cliente.get(ROTA, parametros)


def nomes_das_categorias(resposta):
    return [c["nome"] for c in resposta.json()["categorias"]]


# --- 200 -----------------------------------------------------------------


def test_sem_login_devolve_o_cardapio_completo_no_formato_do_contrato(
    cliente, campus, almoco
):
    resposta = pedir(cliente, campus=campus.pk)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "campus": campus.pk,
        "refeicao": "almoco",
        "data": "2026-11-24",
        "refeicaoEncerrada": False,
        "status": "publicado",
        "avisoSujeitoAAlteracao": AVISO_SUJEITO_A_ALTERACAO,
        "alergenosIndisponivel": False,
        "filtroMarcadorDesativado": False,
        "categorias": [
            {
                "nome": "Salada",
                "semOpcaoCompativel": False,
                "pratos": [
                    {
                        "descricao": "Alface",
                        "marcadores": [],
                        "contemMarcadorSelecionado": False,
                    }
                ],
            },
            {
                "nome": "Prato principal",
                "semOpcaoCompativel": False,
                "pratos": [
                    {
                        "descricao": "Frango assado",
                        "marcadores": ["pimenta"],
                        "contemMarcadorSelecionado": False,
                    }
                ],
            },
            {
                "nome": "Prato principal ovolactovegetariano",
                "semOpcaoCompativel": False,
                "pratos": [
                    {
                        "descricao": "Omelete",
                        "marcadores": ["leite_e_derivados", "ovo"],
                        "contemMarcadorSelecionado": False,
                    }
                ],
            },
            {
                "nome": "Prato principal vegetariano estrito",
                "semOpcaoCompativel": False,
                "pratos": [
                    {
                        "descricao": "Tofu grelhado",
                        "marcadores": ["soja"],
                        "contemMarcadorSelecionado": False,
                    }
                ],
            },
        ],
    }


def test_quem_esta_logado_recebe_o_mesmo_cardapio(cliente, campus, almoco, usuario):
    anonimo = pedir(APIClient(), campus=campus.pk).json()
    cliente.force_login(usuario)

    logado = pedir(cliente, campus=campus.pk)

    assert logado.status_code == 200
    assert logado.json() == anonimo


def test_dieta_e_marcadores_pela_query_string(cliente, campus, almoco):
    resposta = pedir(
        cliente,
        campus=campus.pk,
        dieta="ovolactovegetariano",
        marcadores="leite_e_derivados",
    )

    assert resposta.status_code == 200
    assert nomes_das_categorias(resposta) == [
        "Salada",
        "Prato principal ovolactovegetariano",
        "Prato principal vegetariano estrito",
    ]
    ovolacto = resposta.json()["categorias"][1]
    assert ovolacto["semOpcaoCompativel"] is True
    assert ovolacto["pratos"][0]["contemMarcadorSelecionado"] is True


def test_vegetariano_estrito_mostra_so_a_linha_estrita(cliente, campus, almoco):
    resposta = pedir(cliente, campus=campus.pk, dieta="vegetariano_estrito")

    assert nomes_das_categorias(resposta) == [
        "Salada",
        "Prato principal vegetariano estrito",
    ]


def test_marcadores_com_espacos_e_repetidos_sao_aceitos(cliente, campus, almoco):
    resposta = pedir(cliente, campus=campus.pk, marcadores=" ovo, soja ,ovo")

    assert resposta.status_code == 200
    marcados = [
        p["descricao"]
        for c in resposta.json()["categorias"]
        for p in c["pratos"]
        if p["contemMarcadorSelecionado"]
    ]
    assert marcados == ["Omelete", "Tofu grelhado"]


@pytest.mark.parametrize("vazio", ["", " "])
def test_marcadores_vazio_e_sem_filtro(cliente, campus, almoco, vazio):
    resposta = pedir(cliente, campus=campus.pk, marcadores=vazio)

    assert resposta.status_code == 200
    assert not any(
        p["contemMarcadorSelecionado"]
        for c in resposta.json()["categorias"]
        for p in c["pratos"]
    )


def test_refeicao_e_dia_pedidos(cliente, campus, almoco):
    resposta = pedir(
        cliente,
        agora=(TERCA, time(16, 0)),
        campus=campus.pk,
        semana="2026-11-23",
        dia="2026-11-24",
        refeicao="almoco",
    )

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert (corpo["refeicao"], corpo["data"], corpo["refeicaoEncerrada"]) == (
        "almoco",
        "2026-11-24",
        True,
    )


def test_refeicao_padrao_segue_o_relogio(cliente, campus, almoco):
    # 19h31: jantar, última do dia, encerrada (RN05, item 3).
    resposta = pedir(cliente, agora=(TERCA, time(19, 31)), campus=campus.pk)

    corpo = resposta.json()
    assert (corpo["refeicao"], corpo["refeicaoEncerrada"]) == ("jantar", True)


def test_domingo_mostra_a_segunda_com_a_data_do_dia_exibido(cliente, campus):
    publicar_semana(campus, SEGUNDA)
    publicar_semana(campus, PROXIMA_SEGUNDA)
    criar_refeicao(campus, PROXIMA_SEGUNDA, TipoRefeicao.CAFE)

    resposta = pedir(cliente, agora=(DOMINGO, time(12, 0)), campus=campus.pk)

    corpo = resposta.json()
    assert (corpo["refeicao"], corpo["data"], corpo["status"]) == (
        "cafe",
        "2026-11-30",
        "publicado",
    )


def test_nao_publicado_volta_200_e_nunca_404(cliente, campus):
    criar_refeicao(campus, TERCA, TipoRefeicao.ALMOCO)

    resposta = pedir(cliente, campus=campus.pk)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == CHAVES_DO_CONTRATO
    assert corpo["status"] == "nao_publicado"
    assert corpo["categorias"] == []
    assert corpo["avisoSujeitoAAlteracao"] == AVISO_SUJEITO_A_ALTERACAO


def test_alergenos_indisponiveis_na_resposta(cliente, campus):
    publicar_semana(campus, SEGUNDA)
    refeicao = criar_refeicao(
        campus, TERCA, TipoRefeicao.ALMOCO, StatusLeitura.ALERGENOS_INDISPONIVEIS
    )
    criar_categoria(refeicao, "Prato principal", 1, [("Tofu", None, ["soja"])])

    resposta = pedir(cliente, campus=campus.pk, marcadores="soja")

    corpo = resposta.json()
    assert corpo["alergenosIndisponivel"] is True
    assert corpo["filtroMarcadorDesativado"] is True
    assert corpo["categorias"][0]["pratos"][0]["contemMarcadorSelecionado"] is False


def test_consultas_nao_crescem_com_o_numero_de_pratos(
    cliente, campus, almoco, django_assert_max_num_queries
):
    with django_assert_max_num_queries(10) as pequeno:
        pedir(cliente, campus=campus.pk)
    for ordem in range(5, 15):
        criar_categoria(
            almoco,
            f"Categoria {ordem}",
            ordem,
            [(f"Prato {ordem}.{n}", None, ["ovo"]) for n in range(5)],
        )

    with django_assert_max_num_queries(len(pequeno.captured_queries)):
        resposta = pedir(cliente, campus=campus.pk)

    assert len(resposta.json()["categorias"]) == 14


def test_o_relogio_e_lido_uma_vez_por_pedido(cliente, campus, almoco):
    agora = em_brasilia(TERCA, time(12, 0))
    with mock.patch("django.utils.timezone.now", return_value=agora) as now:
        resposta = cliente.get(ROTA, {"campus": campus.pk})

    assert resposta.status_code == 200
    assert now.call_count == 1


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_metodos_de_escrita_dao_405(cliente, campus, metodo):
    resposta = getattr(cliente, metodo)(ROTA, {"campus": campus.pk}, format="json")

    assert resposta.status_code == 405


# --- 400 parametros_invalidos ----------------------------------------------


def assert_400(resposta, trecho=None):
    assert resposta.status_code == 400
    corpo = resposta.json()
    # Formato do projeto, nunca o padrão de validação do DRF.
    assert set(corpo) == {"codigo", "mensagem"}
    assert corpo["codigo"] == "parametros_invalidos"
    assert isinstance(corpo["mensagem"], str)
    assert corpo["mensagem"]
    if trecho is not None:
        assert trecho in corpo["mensagem"]


def test_sem_campus_da_400(cliente, db):
    assert_400(pedir(cliente), "campus")


@pytest.mark.parametrize("valor", ["", "abc", "1.5", "-1", "gama", " 1", "1e2", "١"])
def test_campus_que_nao_e_inteiro_da_400(cliente, campus, valor):
    assert_400(pedir(cliente, campus=valor), "campus")


def test_campus_inexistente_da_400(cliente, campus):
    resposta = pedir(cliente, campus=campus.pk + 100)
    assert_400(resposta)
    assert resposta.json()["mensagem"] == "Não existe campus com esse id."


@pytest.mark.parametrize("parametro", ["semana", "dia"])
@pytest.mark.parametrize(
    "valor", ["2026-13-01", "2026-02-30", "23/11/2026", "20261123", "amanha", ""]
)
def test_data_invalida_da_400(cliente, campus, parametro, valor):
    assert_400(pedir(cliente, campus=campus.pk, **{parametro: valor}), parametro)


def test_dia_fora_da_semana_pedida_da_400(cliente, campus):
    assert_400(
        pedir(cliente, campus=campus.pk, semana="2026-11-23", dia="2026-11-30"),
        "semana",
    )


@pytest.mark.parametrize("valor", ["lanche", "ALMOCO", "almoço", ""])
def test_refeicao_fora_do_enum_da_400(cliente, campus, valor):
    assert_400(pedir(cliente, campus=campus.pk, refeicao=valor), "refeição")


@pytest.mark.parametrize("valor", ["vegano", "ovolacto", "padrao", ""])
def test_dieta_fora_do_enum_da_400(cliente, campus, valor):
    assert_400(pedir(cliente, campus=campus.pk, dieta=valor), "dieta")


def test_marcador_desconhecido_da_400_com_o_nome(cliente, campus):
    # Ignorar em silêncio um alergênico escrito errado mostraria o cardápio
    # sem alerta, como se fosse seguro (decisão de 21/11/2026).
    resposta = pedir(cliente, campus=campus.pk, marcadores="leite")

    assert_400(resposta)
    assert resposta.json()["mensagem"] == "Marcador desconhecido: leite."


def test_marcador_invalido_no_meio_de_validos_da_400(cliente, campus):
    resposta = pedir(cliente, campus=campus.pk, marcadores="ovo,leite,soja")

    assert_400(resposta)
    assert resposta.json()["mensagem"] == "Marcador desconhecido: leite."


def test_varios_marcadores_desconhecidos_saem_todos_na_mensagem(cliente, campus):
    resposta = pedir(cliente, campus=campus.pk, marcadores="leite, ovo,gluten,leite")

    assert_400(resposta)
    assert resposta.json()["mensagem"] == "Marcadores desconhecidos: leite, gluten."


@pytest.mark.parametrize("valor", ["ovo,,soja", ",ovo", "ovo,", "ovo, ,soja"])
def test_item_vazio_em_marcadores_da_400(cliente, campus, valor):
    assert_400(pedir(cliente, campus=campus.pk, marcadores=valor), "marcadores")


def test_marcador_existe_na_tabela_e_nao_numa_lista_fixa(cliente, campus):
    # A lista vem da tabela MARCADOR (fixture da BD-03).
    from apps.cardapio.models import Marcador

    Marcador.objects.filter(nome="mel").delete()

    assert_400(pedir(cliente, campus=campus.pk, marcadores="mel"), "mel")


# --- Revisão do PR #214: parâmetro repetido, desconhecido e datas extremas ---


@pytest.mark.parametrize(
    "query",
    [
        "marcadores=ovo&marcadores=soja",
        "dieta=sem_filtro&dieta=vegetariano_estrito",
        "refeicao=almoco&refeicao=jantar",
        "dia=2026-11-24&dia=2026-11-25",
    ],
)
def test_parametro_repetido_da_400(cliente, campus, almoco, query):
    # `QueryDict.get` ficaria só com o último valor: com marcadores, o `ovo`
    # sumiria sem aviso.
    with relogio(TERCA, time(12, 0)):
        resposta = cliente.get(f"{ROTA}?campus={campus.pk}&{query}")

    assert_400(resposta, "mais de uma vez")


def test_campus_repetido_da_400(cliente, campus):
    with relogio(TERCA, time(12, 0)):
        resposta = cliente.get(f"{ROTA}?campus={campus.pk}&campus={campus.pk}")

    assert_400(resposta, "campus")


@pytest.mark.parametrize("nome", ["marcadores[]", "marcador", "Marcadores", "dietas"])
def test_parametro_desconhecido_da_400_com_o_nome(cliente, campus, almoco, nome):
    # Um filtro de alergênico com o nome errado não pode virar "sem filtro".
    resposta = pedir(cliente, campus=campus.pk, **{nome: "ovo"})

    assert_400(resposta)
    assert resposta.json()["mensagem"] == f"Parâmetro desconhecido: {nome}."


def test_varios_parametros_desconhecidos_saem_todos(cliente, campus):
    resposta = pedir(cliente, campus=campus.pk, marcador="ovo", tipo="almoco")

    assert_400(resposta)
    assert resposta.json()["mensagem"] == "Parâmetros desconhecidos: marcador, tipo."


@pytest.mark.parametrize("parametro", ["semana", "dia"])
@pytest.mark.parametrize(
    "valor", ["0001-01-01", "1999-12-31", "2100-01-01", "9999-12-31"]
)
def test_data_fora_da_faixa_aceita_da_400_e_nao_500(cliente, campus, parametro, valor):
    resposta = pedir(cliente, campus=campus.pk, refeicao="almoco", **{parametro: valor})

    assert_400(resposta, parametro)


@pytest.mark.parametrize("valor", ["2000-01-01", "2099-12-31"])
def test_datas_nos_limites_da_faixa_sao_aceitas(cliente, campus, valor):
    resposta = pedir(cliente, campus=campus.pk, dia=valor, refeicao="almoco")

    assert resposta.status_code == 200
    assert resposta.json()["data"] == valor


def test_semana_e_dia_nos_extremos_da_faixa(cliente, campus):
    resposta = pedir(cliente, campus=campus.pk, semana="2099-12-30", dia="2099-12-31")

    assert resposta.status_code == 200


@pytest.mark.parametrize(
    "dia, valido",
    [
        ("2026-11-22", False),  # semana - 1
        ("2026-11-23", True),  # primeiro dia
        ("2026-11-29", True),  # semana + 6
        ("2026-11-30", False),  # semana + 7
    ],
)
def test_limites_do_dia_dentro_da_semana(cliente, campus, dia, valido):
    resposta = pedir(cliente, campus=campus.pk, semana="2026-11-23", dia=dia)

    if valido:
        assert resposta.status_code == 200
        assert resposta.json()["data"] == dia
    else:
        assert_400(resposta, "semana")
