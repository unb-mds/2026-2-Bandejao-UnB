"""Bloco `pontos` de ponta a ponta (BE-14, RF24.2, RN09).

Avaliar antes do check-in não pontua; o check-in depois traz os 10 dele e
libera os 5 da avaliação. O cliente exige CSRF, como o navegador (#112).
"""

from datetime import date, time
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_refeicao, em_brasilia
from apps.fila.tests.apoio import RU_DARCY, ao_norte, criar_campus
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from config.parametros import AvisoPrivacidadeConfig

pytestmark = pytest.mark.django_db

TERCA = date(2026, 11, 24)
DURANTE_O_ALMOCO = em_brasilia(TERCA, time(12, 7))
NO_RU = ao_norte(RU_DARCY, 20)


@pytest.fixture
def conta(db):
    return get_user_model().objects.create_user(
        matricula_siape="202400301",
        tipo_usuario="estudante",
        apelido="ponta",
        email_institucional="202400301@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita=AvisoPrivacidadeConfig.versao_atual,
        password="senha-forte-123",
    )


@pytest.fixture
def logado(conta):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(conta)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    return cliente


@pytest.fixture
def darcy(db):
    return criar_campus()


def postar(cliente, rota, dados):
    with mock.patch("django.utils.timezone.now", return_value=DURANTE_O_ALMOCO):
        return cliente.post(rota, dados, format="json")


def avaliar(cliente, refeicao, nota=4):
    return postar(
        cliente, "/api/avaliacoes/", {"refeicaoId": refeicao.id, "nota": nota}
    )


def fazer_checkin(cliente, campus):
    return postar(
        cliente,
        "/api/checkins/",
        {
            "campus": campus.id,
            "tipoRefeicao": "almoco",
            "coordenadas": {"latitude": NO_RU.latitude, "longitude": NO_RU.longitude},
        },
    )


def test_avaliacao_antes_e_checkin_depois_libera_os_5_pontos(logado, conta, darcy):
    almoco = criar_refeicao(darcy, TERCA, TipoRefeicao.ALMOCO)

    avaliacao = avaliar(logado, almoco)
    checkin = fazer_checkin(logado, darcy)

    assert avaliacao.status_code == 201
    assert avaliacao.json()["pontos"] == {
        "total": 0,
        "contribuicao": 0,
        "avaliacaoLiberada": 0,
    }
    assert checkin.status_code == 201
    assert checkin.json()["pontos"] == {
        "total": 15,
        "contribuicao": 10,
        "avaliacaoLiberada": 5,
    }
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 15
    assert PontosSemestreCampus.objects.get(usuario=conta, campus=darcy).pontos == 15


def test_checkin_antes_e_avaliacao_depois_pontua_na_avaliacao(logado, conta, darcy):
    almoco = criar_refeicao(darcy, TERCA, TipoRefeicao.ALMOCO)

    fazer_checkin(logado, darcy)
    primeira = avaliar(logado, almoco, nota=4)
    editada = avaliar(logado, almoco, nota=2)

    assert primeira.json()["pontos"] == {
        "total": 5,
        "contribuicao": 5,
        "avaliacaoLiberada": 0,
    }
    # A edição chama a pontuação de novo, mas não pontua em dobro.
    assert editada.status_code == 200
    assert editada.json()["pontos"]["total"] == 0
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 15
