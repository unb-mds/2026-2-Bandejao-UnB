"""Consultas públicas da avaliação (BE-13, RF15.2, RF20.3, RI10, RNF08, N4 4b).

GET /api/refeicoes/{refeicaoId}/avaliacoes/ e GET /api/avaliacoes/resumo/.
"""

from datetime import UTC, datetime, time
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.avaliacao.tests.apoio import DURANTE_O_ALMOCO, QUARTA, SEGUNDA, TERCA, avaliar
from apps.avaliacao.tests.conftest import criar_conta
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_campus, criar_refeicao, em_brasilia

pytestmark = pytest.mark.django_db


def comentarios_de(refeicao_id):
    return APIClient().get(f"/api/refeicoes/{refeicao_id}/avaliacoes/")


def resumo(agora=DURANTE_O_ALMOCO, **parametros):
    with mock.patch("django.utils.timezone.now", return_value=agora):
        return APIClient().get("/api/avaliacoes/resumo/", parametros)


def assert_erro(resposta, situacao, codigo):
    assert resposta.status_code == situacao
    assert set(resposta.json()) == {"codigo", "mensagem"}
    assert resposta.json()["codigo"] == codigo


# --- GET /api/refeicoes/{refeicaoId}/avaliacoes/ -----------------------------


def test_comentarios_com_apelido_media_e_quantidade_sem_login(
    conta, outra_conta, almoco
):
    with mock.patch(
        "django.utils.timezone.now", return_value=em_brasilia(TERCA, time(12, 0))
    ):
        avaliar(conta, almoco, nota=5, comentario="Feijão ótimo")
    with mock.patch(
        "django.utils.timezone.now", return_value=em_brasilia(TERCA, time(13, 0))
    ):
        avaliar(outra_conta, almoco, nota=2)

    resposta = comentarios_de(almoco.id)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "resumoAvaliacoes": {"media": 3.5, "quantidade": 2},
        "comentarios": [
            {
                "apelido": "rafa",
                "nota": 2,
                "comentario": "",
                "criadaEm": "2026-11-24T13:00:00-03:00",
            },
            {
                "apelido": "dani",
                "nota": 5,
                "comentario": "Feijão ótimo",
                "criadaEm": "2026-11-24T12:00:00-03:00",
            },
        ],
    }


def test_refeicao_sem_avaliacoes(almoco):
    resposta = comentarios_de(almoco.id)

    assert resposta.json() == {
        "resumoAvaliacoes": {"media": None, "quantidade": 0},
        "comentarios": [],
    }


def test_avaliacao_oculta_nao_aparece_nem_entra_na_media(conta, outra_conta, almoco):
    avaliar(conta, almoco, nota=5)
    avaliar(outra_conta, almoco, nota=1, comentario="ofensa", oculta=True)

    corpo = comentarios_de(almoco.id).json()

    assert corpo["resumoAvaliacoes"] == {"media": 5.0, "quantidade": 1}
    assert [c["apelido"] for c in corpo["comentarios"]] == ["dani"]
    assert "ofensa" not in str(corpo)


def test_conta_removida_aparece_como_usuario_removido(conta, almoco):
    avaliar(conta, almoco, nota=4, comentario="Bom")
    conta.delete()

    corpo = comentarios_de(almoco.id).json()

    assert corpo["resumoAvaliacoes"] == {"media": 4.0, "quantidade": 1}
    assert corpo["comentarios"][0]["apelido"] == "usuário removido"
    assert corpo["comentarios"][0]["comentario"] == "Bom"


def test_refeicao_de_dias_passados_continua_visivel(conta, gama):
    """RF15.2: a semana vigente inteira, inclusive dias que já passaram."""
    segunda = criar_refeicao(gama, SEGUNDA)
    avaliar(conta, segunda, nota=3)

    assert comentarios_de(segunda.id).json()["resumoAvaliacoes"]["quantidade"] == 1


def test_comentarios_nao_trazem_matricula_nem_email(conta, outra_conta, almoco):
    """Teste da ADR 0008 (RI10): só os campos do contrato, nada do autor além
    do apelido."""
    avaliar(conta, almoco, comentario="Bom")
    avaliar(outra_conta, almoco)

    resposta = comentarios_de(almoco.id)

    conteudo = resposta.content.decode()
    for autor in (conta, outra_conta):
        assert autor.matricula_siape not in conteudo
        assert autor.email_institucional not in conteudo
    assert "@" not in conteudo
    for comentario in resposta.json()["comentarios"]:
        assert set(comentario) == {"apelido", "nota", "comentario", "criadaEm"}


def test_comentarios_custam_um_numero_fixo_de_consultas(conta, outra_conta, almoco):
    avaliar(conta, almoco)
    avaliar(outra_conta, almoco)
    with CaptureQueriesContext(connection) as poucas:
        comentarios_de(almoco.id)
    for numero in range(13, 18):
        avaliar(criar_conta(numero, f"conta{numero}"), almoco)

    with CaptureQueriesContext(connection) as muitas:
        comentarios_de(almoco.id)

    assert len(muitas) == len(poucas)


@pytest.mark.parametrize("refeicao_id", [999_999, 10**30])
def test_refeicao_inexistente_da_404(db, refeicao_id):
    assert_erro(comentarios_de(refeicao_id), 404, "refeicao_nao_encontrada")


# --- GET /api/avaliacoes/resumo/ ---------------------------------------------


def test_resumo_do_dia_sem_login(conta, outra_conta, gama):
    cafe = criar_refeicao(gama, TERCA, TipoRefeicao.CAFE)
    almoco = criar_refeicao(gama, TERCA, TipoRefeicao.ALMOCO)
    avaliar(conta, almoco, nota=5)
    avaliar(outra_conta, almoco, nota=4)
    avaliar(conta, cafe, nota=3, oculta=True)

    resposta = resumo(campus=gama.id, data="2026-11-24")

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"refeicaoId": cafe.id, "tipo": "cafe", "media": None, "quantidade": 0},
        {"refeicaoId": almoco.id, "tipo": "almoco", "media": 4.5, "quantidade": 2},
    ]


def test_sem_data_o_resumo_e_do_dia_de_brasilia(conta, gama):
    terca = criar_refeicao(gama, TERCA)
    criar_refeicao(gama, QUARTA)
    # 22h de terça em Brasília, 1h de quarta em UTC (o relógio do servidor).
    noite_de_terca = datetime(2026, 11, 25, 1, 0, tzinfo=UTC)

    resposta = resumo(agora=noite_de_terca, campus=gama.id)

    assert [r["refeicaoId"] for r in resposta.json()] == [terca.id]


def test_dia_sem_refeicoes_da_lista_vazia(gama):
    resposta = resumo(campus=gama.id, data="2026-11-29")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_resumo_so_do_campus_pedido(conta, gama):
    darcy = criar_campus("Darcy Ribeiro")
    criar_refeicao(darcy, TERCA)

    assert resumo(campus=gama.id, data="2026-11-24").json() == []


def test_resumo_nao_traz_dado_do_autor(conta, almoco):
    avaliar(conta, almoco, comentario="Bom")

    conteudo = resumo(campus=almoco.campus.id, data="2026-11-24").content.decode()

    assert "dani" not in conteudo
    assert "Bom" not in conteudo
    assert conta.matricula_siape not in conteudo


@pytest.mark.parametrize(
    "parametros",
    [
        {},
        {"data": "2026-11-24"},
        {"campus": "abc"},
        {"campus": " 1"},
        {"campus": "-1"},
        {"campus": "GAMA", "data": "24/11/2026"},
        {"campus": "GAMA", "data": "20261124"},
        {"campus": "GAMA", "data": "2026-02-30"},
        {"campus": "GAMA", "data": "1999-12-31"},
        {"campus": "GAMA", "refeicao": "almoco"},
    ],
)
def test_parametro_ausente_ou_invalido_da_400(gama, parametros):
    if parametros.get("campus") == "GAMA":
        parametros = {**parametros, "campus": gama.id}

    assert_erro(resumo(**parametros), 400, "parametros_invalidos")


def test_parametro_repetido_da_400(gama):
    resposta = APIClient().get(
        f"/api/avaliacoes/resumo/?campus={gama.id}&campus={gama.id}"
    )

    assert_erro(resposta, 400, "parametros_invalidos")


@pytest.mark.parametrize("campus", ["999999", "9" * 30])
def test_campus_inexistente_da_404(db, campus):
    assert_erro(resumo(campus=campus), 404, "campus_nao_encontrado")


def test_campus_inexistente_com_data_invalida_da_400(db):
    """Mesmo critério do cardápio (#217): o 400 ganha do 404."""
    assert_erro(resumo(campus="999999", data="ontem"), 400, "parametros_invalidos")
