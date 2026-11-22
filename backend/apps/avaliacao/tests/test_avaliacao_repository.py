"""AvaliacaoRepository: consultas públicas sem as ocultas (RF15.2, RNF08, N4 4b)."""

from datetime import time
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.avaliacao.avaliacao_repository import (
    AvaliacaoRepository,
    ResumoAvaliacoes,
    ResumoRefeicao,
)
from apps.avaliacao.tests.apoio import QUARTA, TERCA, avaliar
from apps.avaliacao.tests.conftest import criar_conta
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_campus, criar_refeicao, em_brasilia

pytestmark = pytest.mark.django_db


# --- listar_por_refeicao -----------------------------------------------------


def test_lista_so_as_avaliacoes_da_refeicao_e_sem_as_ocultas(
    conta, outra_conta, almoco
):
    visivel = avaliar(conta, almoco, nota=4)
    avaliar(outra_conta, almoco, nota=1, oculta=True)
    jantar = criar_refeicao(almoco.campus, TERCA, TipoRefeicao.JANTAR)
    avaliar(conta, jantar)

    assert AvaliacaoRepository().listar_por_refeicao(almoco) == [visivel]


def test_lista_da_mais_nova_para_a_mais_antiga(conta, outra_conta, almoco):
    with mock.patch(
        "django.utils.timezone.now", return_value=em_brasilia(TERCA, time(12, 0))
    ):
        antiga = avaliar(conta, almoco)
    with mock.patch(
        "django.utils.timezone.now", return_value=em_brasilia(TERCA, time(13, 0))
    ):
        nova = avaliar(outra_conta, almoco)

    assert AvaliacaoRepository().listar_por_refeicao(almoco) == [nova, antiga]


def test_listar_e_ler_o_apelido_custa_uma_consulta(conta, outra_conta, almoco):
    avaliar(conta, almoco)
    avaliar(outra_conta, almoco)

    with CaptureQueriesContext(connection) as consultas:
        apelidos = [
            a.usuario.apelido for a in AvaliacaoRepository().listar_por_refeicao(almoco)
        ]

    assert sorted(apelidos) == ["dani", "rafa"]
    assert len(consultas) == 1


def test_listar_nao_carrega_matricula_nem_email_do_autor(conta, almoco):
    """Defesa da RI10: o dado pessoal nem sai do banco nessa consulta."""
    avaliar(conta, almoco)

    with CaptureQueriesContext(connection) as consultas:
        AvaliacaoRepository().listar_por_refeicao(almoco)

    sql = consultas[0]["sql"].lower()
    assert "matricula" not in sql
    assert "email" not in sql


# --- media_e_quantidade ------------------------------------------------------


def test_media_e_quantidade_ignoram_as_ocultas(conta, outra_conta, almoco):
    terceira = criar_conta(13, "lia")
    avaliar(conta, almoco, nota=5)
    avaliar(outra_conta, almoco, nota=2)
    avaliar(terceira, almoco, nota=1, oculta=True)

    assert AvaliacaoRepository().media_e_quantidade(almoco) == ResumoAvaliacoes(
        media=3.5, quantidade=2
    )


def test_sem_avaliacoes_a_media_e_nula(almoco):
    assert AvaliacaoRepository().media_e_quantidade(almoco) == ResumoAvaliacoes(
        media=None, quantidade=0
    )


def test_media_e_float(conta, almoco):
    """No MySQL o AVG volta Decimal; o contrato é número."""
    avaliar(conta, almoco, nota=4)

    assert type(AvaliacaoRepository().media_e_quantidade(almoco).media) is float


# --- resumos_do_dia ----------------------------------------------------------


def test_resumo_traz_cada_refeicao_do_dia_na_ordem_do_anexo_a(conta, outra_conta, gama):
    jantar = criar_refeicao(gama, TERCA, TipoRefeicao.JANTAR)
    cafe = criar_refeicao(gama, TERCA, TipoRefeicao.CAFE)
    almoco = criar_refeicao(gama, TERCA, TipoRefeicao.ALMOCO)
    avaliar(conta, almoco, nota=5)
    avaliar(outra_conta, almoco, nota=4)
    avaliar(conta, jantar, nota=2)

    assert AvaliacaoRepository().resumos_do_dia(gama, TERCA) == [
        ResumoRefeicao(refeicao_id=cafe.id, tipo="cafe", media=None, quantidade=0),
        ResumoRefeicao(refeicao_id=almoco.id, tipo="almoco", media=4.5, quantidade=2),
        ResumoRefeicao(refeicao_id=jantar.id, tipo="jantar", media=2.0, quantidade=1),
    ]


def test_resumo_ignora_as_ocultas(conta, outra_conta, almoco):
    avaliar(conta, almoco, nota=5)
    avaliar(outra_conta, almoco, nota=1, oculta=True)

    [resumo] = AvaliacaoRepository().resumos_do_dia(almoco.campus, TERCA)

    assert (resumo.media, resumo.quantidade) == (5.0, 1)


def test_resumo_com_so_avaliacoes_ocultas_fica_sem_media(conta, almoco):
    avaliar(conta, almoco, nota=1, oculta=True)

    [resumo] = AvaliacaoRepository().resumos_do_dia(almoco.campus, TERCA)

    assert (resumo.media, resumo.quantidade) == (None, 0)


def test_resumo_nao_mistura_outro_dia_nem_outro_campus(conta, almoco):
    darcy = criar_campus("Darcy Ribeiro")
    avaliar(conta, criar_refeicao(darcy, TERCA), nota=1)
    avaliar(conta, criar_refeicao(almoco.campus, QUARTA), nota=1)
    avaliar(conta, almoco, nota=5)

    [resumo] = AvaliacaoRepository().resumos_do_dia(almoco.campus, TERCA)

    assert (resumo.refeicao_id, resumo.media, resumo.quantidade) == (
        almoco.id,
        5.0,
        1,
    )


def test_dia_sem_refeicoes_da_lista_vazia(gama):
    assert AvaliacaoRepository().resumos_do_dia(gama, TERCA) == []


def test_resumo_do_dia_e_uma_consulta_so(conta, outra_conta, gama):
    for tipo in TipoRefeicao.values:
        refeicao = criar_refeicao(gama, TERCA, tipo)
        avaliar(conta, refeicao)
        avaliar(outra_conta, refeicao)

    with CaptureQueriesContext(connection) as consultas:
        resumos = AvaliacaoRepository().resumos_do_dia(gama, TERCA)

    assert len(resumos) == 3
    assert len(consultas) == 1
    assert all(type(r.media) is float for r in resumos)
