"""GET /api/fila/previsao/ (BE-15, RF13, RN06, Fila N4 4c).

Pública e só com agregados. Mesmo critério de parâmetros do cardápio e do
resumo das avaliações (#217): todos os 400 `parametros_invalidos` antes do
404 `campus_nao_encontrado`.
"""

from datetime import UTC, datetime, time
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.fila.checkin_service import CheckinService
from apps.fila.tests.apoio import RU_DARCY, ao_norte
from apps.fila.tests.apoio_previsao import (
    DUAS,
    JANELA,
    MEIO_DIA_DA_QUARTA,
    PROXIMA_QUARTA,
    QUARTA,
    TERCA_PASSADA,
    TRES,
    UMA,
    mesmo_movimento,
)

ROTA = "/api/fila/previsao/"


@pytest.fixture
def cliente():
    return APIClient()


def consultar(cliente, agora=MEIO_DIA_DA_QUARTA, **parametros):
    """GET com o relógio parado: por padrão, ao meio-dia da quarta."""
    with mock.patch("django.utils.timezone.now", return_value=agora):
        return cliente.get(ROTA, parametros)


def previsao_de(cliente, campus, refeicao="almoco", data=QUARTA, **extras):
    return consultar(
        cliente, campus=campus.id, refeicao=refeicao, data=data.isoformat(), **extras
    )


# --- 200 ----------------------------------------------------------------------


def test_previsao_disponivel_sem_login(cliente, darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {time(11, 0): 1, time(12, 0): 4})

    resposta = previsao_de(cliente, darcy)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["campus"] == darcy.id
    assert corpo["tipoRefeicao"] == "almoco"
    assert corpo["data"] == "2026-11-25"
    assert corpo["status"] == "disponivel"
    assert len(corpo["faixas"]) == 14
    assert corpo["faixas"][0] == {
        "inicio": "11:00:00",
        "fim": "11:15:00",
        "nivel": "curta",
        "ehPico": False,
    }
    assert corpo["faixas"][4] == {
        "inicio": "12:00:00",
        "fim": "12:15:00",
        "nivel": "longa",
        "ehPico": True,
    }
    assert corpo["faixas"][-1]["fim"] == "14:30:00"


def test_dados_insuficientes_e_200_com_faixas_vazias(cliente, darcy):
    mesmo_movimento(darcy, [UMA, DUAS], {time(11, 0): 10})

    resposta = previsao_de(cliente, darcy)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "campus": darcy.id,
        "tipoRefeicao": "almoco",
        "data": "2026-11-25",
        "status": "dados_insuficientes",
        "faixas": [],
    }


def test_empate_marca_todas_as_faixas_mais_cheias(cliente, darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {time(11, 30): 3, time(13, 0): 3})

    faixas = previsao_de(cliente, darcy).json()["faixas"]

    assert [f["inicio"] for f in faixas if f["ehPico"]] == ["11:30:00", "13:00:00"]
    assert {f["nivel"] for f in faixas if f["ehPico"]} == {"longa"}


def test_resposta_so_tem_agregados(cliente, darcy):
    """Nada de conta, check-in individual, contagem ou média (RF13, ADR 0008)."""
    mesmo_movimento(darcy, JANELA, {time(11, 0): 2})

    corpo = previsao_de(cliente, darcy).json()

    assert set(corpo) == {"campus", "tipoRefeicao", "data", "status", "faixas"}
    assert {chave for faixa in corpo["faixas"] for chave in faixa} == {
        "inicio",
        "fim",
        "nivel",
        "ehPico",
    }


def test_logado_recebe_a_mesma_previsao(cliente, darcy, conta):
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {time(11, 0): 1})
    anonima = previsao_de(cliente, darcy).json()

    logado = APIClient()
    logado.force_login(conta)

    assert previsao_de(logado, darcy).json() == anonima


def test_cafe_e_jantar_tem_as_faixas_do_seu_horario(cliente, darcy):
    cafe = previsao_de(cliente, darcy, refeicao="cafe").json()
    jantar = previsao_de(cliente, darcy, refeicao="jantar").json()

    assert cafe["tipoRefeicao"] == "cafe"
    assert jantar["status"] == "dados_insuficientes"
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {time(7, 30): 1}, "cafe")
    faixas = previsao_de(cliente, darcy, refeicao="cafe").json()["faixas"]
    assert (faixas[0]["inicio"], faixas[-1]["fim"]) == ("07:00:00", "09:30:00")


# --- Fuso horário ---------------------------------------------------------------


def test_sem_data_usa_o_dia_de_hoje_em_brasilia(cliente, darcy):
    """Às 23h30 de quarta em Brasília já é quinta em UTC: a previsão é de
    quarta, com a janela das quartas."""
    mesmo_movimento(darcy, [UMA, DUAS, TRES], {time(11, 0): 1})
    quinta_em_utc = datetime(2026, 11, 26, 2, 30, tzinfo=UTC)

    resposta = consultar(cliente, quinta_em_utc, campus=darcy.id, refeicao="almoco")

    assert resposta.json()["data"] == "2026-11-25"
    assert resposta.json()["status"] == "disponivel"


def test_faixa_do_checkin_e_a_do_horario_local(cliente, darcy, conta):
    """Check-ins feitos às 15h07 UTC (12h07 em Brasília) caem na faixa das
    12h00, e não na das 15h00, que nem existe no almoço."""
    perto_do_ru = ao_norte(RU_DARCY, 20)
    for dia in (UMA, DUAS, TRES):
        agora = datetime(dia.year, dia.month, dia.day, 15, 7, tzinfo=UTC)
        CheckinService().registrar(conta, darcy, "almoco", perto_do_ru, agora)

    faixas = previsao_de(cliente, darcy).json()["faixas"]

    assert [f["inicio"] for f in faixas if f["ehPico"]] == ["12:00:00"]


def test_data_futura_nao_conta_os_checkins_de_hoje_em_brasilia(cliente, darcy):
    """Às 23h30 de quarta em Brasília (quinta em UTC), pedida a quarta
    seguinte: o "hoje" que sai da janela é a quarta, e não a quinta."""
    mesmo_movimento(darcy, [QUARTA, UMA, DUAS], {time(11, 0): 1})
    quinta_em_utc = datetime(2026, 11, 26, 2, 30, tzinfo=UTC)

    resposta = consultar(
        cliente,
        quinta_em_utc,
        campus=darcy.id,
        refeicao="almoco",
        data=PROXIMA_QUARTA.isoformat(),
    )

    assert resposta.json()["data"] == "2026-12-02"
    assert resposta.json()["status"] == "dados_insuficientes"


def test_outro_dia_da_semana_nao_conta(cliente, darcy):
    mesmo_movimento(darcy, [UMA, DUAS, TERCA_PASSADA], {time(11, 0): 1})

    assert previsao_de(cliente, darcy).json()["status"] == "dados_insuficientes"


# --- 400 e 404 ----------------------------------------------------------------


def codigo(resposta):
    return resposta.status_code, resposta.json()["codigo"]


@pytest.mark.parametrize(
    "parametros",
    [
        {"refeicao": "almoco"},
        {"campus": "abc", "refeicao": "almoco"},
        {"campus": "1", "refeicao": "lanche"},
        {"campus": "1"},
        {"campus": "1", "refeicao": "almoco", "data": "25/11/2026"},
        {"campus": "1", "refeicao": "almoco", "data": "2026-02-30"},
        {"campus": "1", "refeicao": "almoco", "data": "1999-12-31"},
        {"campus": "1", "refeicao": "almoco", "dia": "2026-11-25"},
    ],
)
def test_parametro_ausente_ou_invalido_da_400(cliente, darcy, parametros):
    assert codigo(consultar(cliente, **parametros)) == (400, "parametros_invalidos")


def test_parametro_repetido_da_400(cliente, darcy):
    resposta = cliente.get(f"{ROTA}?campus={darcy.id}&refeicao=almoco&refeicao=jantar")

    assert codigo(resposta) == (400, "parametros_invalidos")


def test_campus_inexistente_da_404(cliente, darcy):
    resposta = consultar(cliente, campus=darcy.id + 100, refeicao="almoco")

    assert codigo(resposta) == (404, "campus_nao_encontrado")


def test_campus_inexistente_com_outro_parametro_invalido_da_400(cliente, darcy):
    resposta = consultar(cliente, campus=darcy.id + 100, refeicao="lanche")

    assert codigo(resposta) == (400, "parametros_invalidos")


def test_mensagem_da_refeicao_invalida_lista_as_opcoes(cliente, darcy):
    resposta = consultar(cliente, campus=darcy.id, refeicao="lanche")

    assert resposta.json()["mensagem"] == (
        "A refeição deve ser cafe, almoco ou jantar."
    )


def test_previsao_faz_poucas_consultas(cliente, darcy, django_assert_num_queries):
    """Campus e contagem: duas consultas, qualquer que seja o volume."""
    mesmo_movimento(darcy, JANELA, {time(11, 0): 3, time(12, 0): 5})

    with django_assert_num_queries(2):
        assert previsao_de(cliente, darcy).status_code == 200
