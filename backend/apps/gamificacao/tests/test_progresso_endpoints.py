"""Progresso e adesão de ponta a ponta (BE-16, RF26.2, RF27.1, ADR 0008).

O cliente exige CSRF, como o navegador (#112). O 401 sem sessão já é coberto
por `tests/test_acesso_contrato.py` e `tests/test_csrf_rotas_reais.py`.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.pontuacao_service import PontuacaoService
from config.parametros import AvisoPrivacidadeConfig, ParametrosGamificacaoConfig

pytestmark = pytest.mark.django_db

PROGRESSO = "/api/gamificacao/progresso/"
ADESAO = "/api/gamificacao/adesao/"

CHAVES_DO_CONTRATO = {
    "patente",
    "pontosTotais",
    "faltaParaProxima",
    "sequencia",
    "diasNaSemana",
    "minimoDias",
    "participaRanking",
}

MATRICULA = "202400501"
EMAIL = "202400501@aluno.unb.br"


@pytest.fixture
def conta(db):
    conta = get_user_model().objects.create_user(
        matricula_siape=MATRICULA,
        tipo_usuario="estudante",
        apelido="edu",
        email_institucional=EMAIL,
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita=AvisoPrivacidadeConfig.versao_atual,
        password="senha-forte-123",
    )
    PontuacaoService().inicializar_conta(conta)
    return conta


@pytest.fixture
def logado(conta):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(conta)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    return cliente


@pytest.fixture
def sem_token(conta):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(conta)
    return cliente


def dar_pontos(conta, pontos):
    PontuacaoUsuario.objects.filter(usuario=conta).update(pontos_totais=pontos)


def chaves_em(valor):
    """Todas as chaves do JSON, em qualquer nível."""
    if isinstance(valor, dict):
        return set(valor) | {
            chave for filho in valor.values() for chave in chaves_em(filho)
        }
    if isinstance(valor, list):
        return {chave for filho in valor for chave in chaves_em(filho)}
    return set()


# --- 5.4 #1 ------------------------------------------------------------------


def test_get_progresso_devolve_as_7_chaves_do_contrato(logado, conta):
    dar_pontos(conta, 460)

    resposta = logado.get(PROGRESSO)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "patente": "VETERANO",
        "pontosTotais": 460,
        "faltaParaProxima": 440,
        "sequencia": 0,
        "diasNaSemana": 0,
        "minimoDias": ParametrosGamificacaoConfig.min_dias_semana,
        "participaRanking": False,
    }
    assert set(resposta.json()) == CHAVES_DO_CONTRATO


def test_get_progresso_nao_cria_a_linha_que_falta(logado, conta):
    PontuacaoUsuario.objects.filter(usuario=conta).delete()

    resposta = logado.get(PROGRESSO)

    assert resposta.status_code == 200
    assert resposta.json()["patente"] == "CALOURO_DE_BANDEJA"
    assert resposta.json()["participaRanking"] is False
    assert not PontuacaoUsuario.objects.filter(usuario=conta).exists()


# --- 5.4 #2, #3 --------------------------------------------------------------


def test_post_adesao_da_204_sem_corpo_e_liga_o_ranking(logado):
    resposta = logado.post(ADESAO)

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert logado.get(PROGRESSO).json()["participaRanking"] is True


def test_delete_adesao_da_204_sem_corpo_e_desliga_o_ranking(logado):
    logado.post(ADESAO)

    resposta = logado.delete(ADESAO)

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert logado.get(PROGRESSO).json()["participaRanking"] is False


def test_post_e_delete_repetidos_continuam_204(logado):
    assert logado.delete(ADESAO).status_code == 204
    assert logado.post(ADESAO).status_code == 204
    assert logado.post(ADESAO).status_code == 204
    assert logado.get(PROGRESSO).json()["participaRanking"] is True


def test_adesao_nao_muda_os_pontos(logado, conta):
    dar_pontos(conta, 200)

    logado.post(ADESAO)
    logado.delete(ADESAO)

    corpo = logado.get(PROGRESSO).json()
    assert corpo["pontosTotais"] == 200
    assert corpo["patente"] == "RATO_DE_RU"


# --- 5.4 #4 ------------------------------------------------------------------


@pytest.mark.parametrize("metodo", ["post", "delete"])
def test_adesao_sem_cabecalho_csrf_da_403(sem_token, conta, metodo):
    resposta = getattr(sem_token, metodo)(ADESAO)

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"
    assert PontuacaoUsuario.objects.get(usuario=conta).participa_ranking is False


# --- 5.4 #6: privacidade (ADR 0008) ------------------------------------------


def test_progresso_sem_dado_pessoal_nem_posicao(logado, conta):
    dar_pontos(conta, 1500)
    logado.post(ADESAO)

    resposta = logado.get(PROGRESSO)

    chaves = {chave.lower() for chave in chaves_em(resposta.json())}
    for proibida in ("matricula", "siape", "email", "posicao", "distintivo"):
        assert not any(proibida in chave for chave in chaves), proibida
    texto = json.dumps(resposta.json())
    assert MATRICULA not in texto
    assert EMAIL not in texto


# --- 5.4 #7: ponta a ponta ---------------------------------------------------


@pytest.mark.parametrize(
    ("pontos", "patente", "falta"),
    [
        (149, "CALOURO_DE_BANDEJA", 1),
        (150, "RATO_DE_RU", 300),
        (1500, "LENDA_DO_RU", 0),
    ],
)
def test_get_progresso_com_pontos_montados_no_banco(
    logado, conta, pontos, patente, falta
):
    dar_pontos(conta, pontos)

    corpo = logado.get(PROGRESSO).json()

    assert corpo["patente"] == patente
    assert corpo["faltaParaProxima"] == falta
