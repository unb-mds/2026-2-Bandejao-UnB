"""GET /api/ranking/{campusId}/ de ponta a ponta (BE-17, RF27.2, RN12, RI12,
ADR 0008).

Rota pública: o visitante vê o ranking sem sessão. O semestre esperado é o
da data de hoje, pelo `SemestreResolver`, para o teste não depender do dia em
que roda.
"""

import json

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cadastro.models import StatusUsuario
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.semestre_resolver import SemestreResolver
from apps.gamificacao.tests.apoio_ranking import criar_conta, pontuar

pytestmark = pytest.mark.django_db


def url(campus_id):
    return f"/api/ranking/{campus_id}/"


@pytest.fixture
def campus(db):
    return criar_campus()


@pytest.fixture
def semestre():
    return SemestreResolver().semestre_de(timezone.localdate())


@pytest.fixture
def visitante():
    return APIClient(enforce_csrf_checks=True)


def dar_pontos_totais(conta, pontos):
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


# --- Formato -----------------------------------------------------------------


def test_visitante_ve_o_ranking_no_formato_do_contrato(visitante, campus, semestre):
    primeira = criar_conta(1)
    segunda = criar_conta(2)
    pontuar(primeira, campus, 40, semestre=semestre)
    pontuar(segunda, campus, 25, semestre=semestre)
    dar_pontos_totais(primeira, 460)
    dar_pontos_totais(segunda, 150)

    resposta = visitante.get(url(campus.pk))

    assert resposta.status_code == 200
    assert resposta.json() == {
        "campusId": campus.pk,
        "semestre": semestre,
        "linhas": [
            {"posicao": 1, "apelido": "conta01", "patente": "VETERANO"},
            {"posicao": 2, "apelido": "conta02", "patente": "RATO_DE_RU"},
        ],
    }


def test_sem_elegiveis_linhas_vem_vazia(visitante, campus, semestre):
    resposta = visitante.get(url(campus.pk))

    assert resposta.status_code == 200
    assert resposta.json() == {
        "campusId": campus.pk,
        "semestre": semestre,
        "linhas": [],
    }


def test_campus_inexistente_da_404(visitante, campus):
    resposta = visitante.get(url(campus.pk + 1))

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "campus_nao_encontrado"


def test_id_maior_que_o_maior_pk_da_404(visitante, campus):
    resposta = visitante.get(url(10**25))

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "campus_nao_encontrado"


# --- Elegibilidade (critérios da issue #185) ---------------------------------


def test_quem_nao_aderiu_nao_aparece(visitante, campus, semestre):
    pontuar(criar_conta(1), campus, 10, semestre=semestre)
    pontuar(criar_conta(2, aderiu=False), campus, 500, semestre=semestre)

    linhas = visitante.get(url(campus.pk)).json()["linhas"]

    assert [linha["apelido"] for linha in linhas] == ["conta01"]


def test_conta_suspensa_nao_aparece(visitante, campus, semestre):
    pontuar(criar_conta(1), campus, 10, semestre=semestre)
    pontuar(
        criar_conta(2, status=StatusUsuario.SUSPENSO), campus, 500, semestre=semestre
    )

    linhas = visitante.get(url(campus.pk)).json()["linhas"]

    assert [linha["apelido"] for linha in linhas] == ["conta01"]


def test_empate_vai_para_quem_pontuou_antes(visitante, campus, semestre):
    pontuar(criar_conta(1), campus, 30, minutos=10, semestre=semestre)
    pontuar(criar_conta(2), campus, 30, minutos=5, semestre=semestre)

    linhas = visitante.get(url(campus.pk)).json()["linhas"]

    assert [(linha["posicao"], linha["apelido"]) for linha in linhas] == [
        (1, "conta02"),
        (2, "conta01"),
    ]


def test_desligar_a_adesao_tira_do_ranking_na_hora(campus, semestre):
    conta = criar_conta(1)
    pontuar(conta, campus, 10, semestre=semestre)
    cliente = APIClient()
    cliente.force_login(conta)
    assert len(cliente.get(url(campus.pk)).json()["linhas"]) == 1

    cliente.delete("/api/gamificacao/adesao/")

    assert cliente.get(url(campus.pk)).json()["linhas"] == []


# --- Privacidade (ADR 0008) --------------------------------------------------


def test_nenhum_ponto_nem_dado_pessoal_na_resposta(visitante, campus, semestre):
    conta = criar_conta(1)
    # Valores que não se confundem com posição nem com o id do campus.
    pontuar(conta, campus, 4321, semestre=semestre)
    dar_pontos_totais(conta, 8765)

    resposta = visitante.get(url(campus.pk))

    chaves = {chave.lower() for chave in chaves_em(resposta.json())}
    for proibida in ("pontos", "distintivo", "matricula", "siape", "email"):
        assert not any(proibida in chave for chave in chaves), proibida
    texto = json.dumps(resposta.json())
    for valor in ("4321", "8765", conta.matricula_siape, conta.email_institucional):
        assert valor not in texto


def test_dez_linhas_sem_uma_consulta_por_linha(
    visitante, campus, semestre, django_assert_max_num_queries
):
    for n in range(1, 11):
        pontuar(criar_conta(n), campus, n, semestre=semestre)

    # Campus, elegíveis e contas com a pontuação.
    with django_assert_max_num_queries(3):
        resposta = visitante.get(url(campus.pk))

    assert len(resposta.json()["linhas"]) == 10
