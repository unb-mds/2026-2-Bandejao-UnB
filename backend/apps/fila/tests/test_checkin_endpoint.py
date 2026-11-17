"""POST /api/checkins/ (BE-09, RF11, RF12, RI03, RI09, Fila N4 4a).

O cliente exige CSRF, como o navegador (#112).
"""

import logging
from datetime import UTC, datetime
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.fila.janela_checkin_validator import JanelaCheckinValidator
from apps.fila.models import Checkin, MotivoRejeicao, TentativaCheckin
from apps.fila.tests.apoio import RU_DARCY, ao_norte
from apps.fila.views import MENSAGENS_RECUSA
from tests.rotas_do_contrato import gerar_schema

ROTA = "/api/checkins/"
# 12h07 em Brasília: dentro do almoço.
AGORA = datetime(2026, 11, 17, 15, 7, tzinfo=UTC)
# 16h em Brasília: entre o almoço e o jantar.
FORA_DO_HORARIO = datetime(2026, 11, 17, 19, 0, tzinfo=UTC)
NO_RU = ao_norte(RU_DARCY, 20)
LONGE = ao_norte(RU_DARCY, 500)

# Posição com casas decimais fáceis de achar em logs e no banco (RI09).
LAT_MARCADA = -15.7641234
LNG_MARCADA = -47.8705678


def cliente_com_csrf():
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    return cliente


@pytest.fixture
def logado(conta):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(conta)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    return cliente


def corpo(campus, coordenadas=NO_RU, tipo="almoco"):
    return {
        "campus": campus.id,
        "tipoRefeicao": tipo,
        "coordenadas": {
            "latitude": coordenadas.latitude,
            "longitude": coordenadas.longitude,
        },
    }


def postar(cliente, dados, agora=AGORA):
    with mock.patch("django.utils.timezone.now", return_value=agora):
        return cliente.post(ROTA, dados, format="json")


# --- 201 ---------------------------------------------------------------------


def test_checkin_confirmado_devolve_201_com_checkin_e_pontos(logado, darcy):
    resposta = postar(logado, corpo(darcy))

    assert resposta.status_code == 201
    checkin = Checkin.objects.get()
    assert resposta.json() == {
        "checkin": {
            "id": checkin.id,
            "campus": darcy.id,
            "tipoRefeicao": "almoco",
            "data": "2026-11-17",
        },
        # Versão mínima da pontuação: a BE-14 passa a conceder os pontos.
        "pontos": {"total": 0, "contribuicao": 0, "avaliacaoLiberada": 0},
    }


def test_data_da_resposta_e_o_dia_de_brasilia(logado, darcy):
    """22h de 17/11 em Brasília já é 18/11 em UTC (horário liberado no teste)."""
    with mock.patch.object(
        JanelaCheckinValidator, "dentro_do_horario", return_value=True
    ):
        resposta = postar(
            logado,
            corpo(darcy, tipo="jantar"),
            agora=datetime(2026, 11, 18, 1, 0, tzinfo=UTC),
        )

    assert resposta.json()["checkin"]["data"] == "2026-11-17"


def test_checkin_e_da_conta_da_sessao(logado, conta, darcy):
    postar(logado, {**corpo(darcy), "usuario": 999, "conta": 999})

    assert Checkin.objects.get().usuario == conta


# --- 401 e 403 ---------------------------------------------------------------


def test_sem_sessao_da_401(darcy):
    resposta = postar(cliente_com_csrf(), corpo(darcy))

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"
    assert not TentativaCheckin.objects.exists()


def test_aviso_pendente_da_403_sem_gravar_tentativa(logado, conta, darcy):
    conta.versao_aviso_aceita = "2020-01-01"
    conta.save()

    resposta = postar(logado, corpo(darcy))

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "aviso_privacidade_pendente"
    assert resposta.json()["mensagem"]
    assert not TentativaCheckin.objects.exists()
    assert not Checkin.objects.exists()


# --- 422 ---------------------------------------------------------------------


def test_fora_do_horario_da_422_com_a_janela_na_mensagem(logado, darcy):
    resposta = postar(logado, corpo(darcy), agora=FORA_DO_HORARIO)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "fora_do_horario"
    assert "11h00" in resposta.json()["mensagem"]
    assert "14h30" in resposta.json()["mensagem"]


def test_checkin_repetido_da_422(logado, darcy):
    postar(logado, corpo(darcy))

    resposta = postar(logado, corpo(darcy))

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "checkin_duplicado"
    assert Checkin.objects.count() == 1


def test_fora_do_raio_da_422(logado, darcy):
    resposta = postar(logado, corpo(darcy, coordenadas=LONGE))

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "localizacao_nao_confirmada"
    assert resposta.json()["mensagem"]
    assert not Checkin.objects.exists()


def test_todo_motivo_de_recusa_tem_mensagem():
    """Motivo novo sem mensagem quebraria o 422 (viraria 500, revisão do #154).

    O `fora_do_horario` monta a mensagem com a janela da refeição.
    """
    com_mensagem_propria = {MotivoRejeicao.FORA_DO_HORARIO}
    assert set(MotivoRejeicao.values) - com_mensagem_propria <= set(MENSAGENS_RECUSA)


# --- Contrato ----------------------------------------------------------------


def test_contrato_publica_os_valores_de_tipo_refeicao():
    """O front lê as refeições aceitas no `enum`, e não na descrição (revisão do #154)."""
    schema = gerar_schema()
    campo = schema["components"]["schemas"]["CheckinEntradaRequest"]["properties"][
        "tipoRefeicao"
    ]
    if "$ref" in campo:
        campo = schema["components"]["schemas"][campo["$ref"].rsplit("/", 1)[-1]]

    assert campo["enum"] == ["cafe", "almoco", "jantar"]


# --- 400: corpo fora do formato ----------------------------------------------


@pytest.mark.parametrize(
    "alterar",
    [
        lambda dados: dados.pop("coordenadas"),
        lambda dados: dados["coordenadas"].update(latitude=95),
        lambda dados: dados["coordenadas"].update(longitude="leste"),
        lambda dados: dados.update(tipoRefeicao="lanche"),
        lambda dados: dados.update(campus=99999),
        lambda dados: dados.pop("campus"),
    ],
    ids=[
        "sem-coordenadas",
        "latitude-fora-da-faixa",
        "longitude-nao-numerica",
        "refeicao-inexistente",
        "campus-inexistente",
        "sem-campus",
    ],
)
def test_corpo_invalido_da_400_sem_gravar_tentativa(logado, darcy, alterar):
    dados = corpo(darcy)
    alterar(dados)

    resposta = postar(logado, dados)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "dados_invalidos"
    assert resposta.json()["mensagem"]
    assert not TentativaCheckin.objects.exists()


# --- RI09: nenhuma coordenada é gravada ou registrada em log -----------------


@pytest.fixture
def log(caplog):
    """`caplog` em DEBUG que também ouve os loggers com `propagate=False`.

    Sem isto o `django.request` (que grava o 500) não chegaria ao `caplog`.
    """
    caplog.set_level(logging.DEBUG)
    isolados = [
        logging.getLogger(nome)
        for nome in ("django.request", "django.db.backends.base")
    ]
    for logger in isolados:
        logger.addHandler(caplog.handler)
    yield caplog
    for logger in isolados:
        logger.removeHandler(caplog.handler)


def coordenada_marcada(campus, latitude=LAT_MARCADA, longitude=LNG_MARCADA):
    dados = corpo(campus)
    dados["coordenadas"] = {"latitude": latitude, "longitude": longitude}
    return dados


def digitos(valor):
    """As casas decimais da coordenada, que é o que um vazamento mostraria."""
    return str(abs(valor)).split(".")[1]


@pytest.mark.parametrize(
    "latitude, longitude, agora",
    [
        (LAT_MARCADA, LNG_MARCADA, AGORA),
        (LAT_MARCADA, LNG_MARCADA, FORA_DO_HORARIO),
        # ~22 km ao sul do RU do Darcy: fora do raio.
        (-15.9641234, LNG_MARCADA, AGORA),
        # Fora da faixa: cai no 400.
        (95.7641234, LNG_MARCADA, AGORA),
    ],
    ids=["confirmado", "fora-do-horario", "fora-do-raio", "invalida"],
)
def test_coordenadas_nao_vao_para_o_log_nem_para_o_banco(
    logado, darcy, log, latitude, longitude, agora
):
    resposta = postar(
        logado, coordenada_marcada(darcy, latitude, longitude), agora=agora
    )

    # Os dígitos procurados são os da posição enviada neste caso (revisão do #154).
    lat, lng = digitos(latitude), digitos(longitude)
    assert lat not in log.text
    assert lng not in log.text
    assert lat not in resposta.content.decode()
    assert lng not in resposta.content.decode()
    gravado = str(list(Checkin.objects.values())) + str(
        list(TentativaCheckin.objects.values())
    )
    assert lat not in gravado
    assert lng not in gravado


def test_erro_inesperado_nao_leva_coordenadas_ao_log(logado, darcy, log):
    """O 500 grava o traceback (django.request), mas não o corpo da requisição."""
    logado.raise_request_exception = False

    with mock.patch(
        "apps.gamificacao.pontuacao_service.PontuacaoService.registrar_contribuicao",
        side_effect=RuntimeError("falhou"),
    ):
        resposta = postar(logado, coordenada_marcada(darcy))

    assert resposta.status_code == 500
    assert "falhou" in log.text
    assert digitos(LAT_MARCADA) not in log.text
    assert digitos(LNG_MARCADA) not in log.text
