"""GET /api/campi/ (BE-08, RF07.2, RI09, Exposição N4 4b).

A lista é pública e só tem `id` e `nome`. O raio de confirmação do RU e as
coordenadas nunca saem (RI09). A resposta vai com `ETag` e
`Cache-Control: private, no-cache`, e o servidor responde 304 sem corpo
quando o `If-None-Match` bate (decisão registrada na #98).

Os campi usam valores marcantes no raio e nas coordenadas, para dar para
procurar esses números no corpo da resposta.
"""

import hashlib
import json
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cardapio.models import Campus

ROTA = "/api/campi/"

# Valores que não podem aparecer em nenhuma resposta.
RU_LATITUDE = Decimal("-15.765432")
RU_LONGITUDE = Decimal("-47.876543")
RAIO_CONFIRMACAO = 4321
CENTRO_LATITUDE = Decimal("-15.712345")
CENTRO_LONGITUDE = Decimal("-47.898765")
RAIO_DETECCAO = 9876


def criar_campus(nome, **kwargs):
    """Campus com os 7 campos NOT NULL e os valores marcantes."""
    dados = {
        "nome": nome,
        "ru_latitude": RU_LATITUDE,
        "ru_longitude": RU_LONGITUDE,
        "raio_confirmacao_metros": RAIO_CONFIRMACAO,
        "centro_latitude": CENTRO_LATITUDE,
        "centro_longitude": CENTRO_LONGITUDE,
        "raio_deteccao_metros": RAIO_DETECCAO,
    }
    dados.update(kwargs)
    return Campus.objects.create(**dados)


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def campi(db):
    """Três campi criados fora da ordem alfabética."""
    return [
        criar_campus("Gama"),
        criar_campus("Darcy Ribeiro"),
        criar_campus("Ceilândia"),
    ]


def esperado(campi):
    return [{"id": c.id, "nome": c.nome} for c in campi]


# --- Resposta pública ------------------------------------------------------


def test_sem_login_devolve_200_com_id_e_nome_em_ordem_de_id(cliente, campi):
    resposta = cliente.get(ROTA)

    assert resposta.status_code == 200
    assert resposta.json() == esperado(campi)


def test_cada_item_tem_exatamente_id_e_nome(cliente, campi):
    resposta = cliente.get(ROTA)

    assert len(resposta.json()) == 3
    for item in resposta.json():
        assert set(item) == {"id", "nome"}
        assert isinstance(item["id"], int)
        assert isinstance(item["nome"], str)


def test_raio_e_coordenadas_nunca_saem_na_resposta(cliente, campi):
    corpo = cliente.get(ROTA).content.decode()

    valores = [
        RU_LATITUDE,
        RU_LONGITUDE,
        RAIO_CONFIRMACAO,
        CENTRO_LATITUDE,
        CENTRO_LONGITUDE,
        RAIO_DETECCAO,
    ]
    for valor in valores:
        assert str(valor) not in corpo
    # Também sem as partes do número (ex.: "765432" sem o sinal e o ponto).
    assert "765432" not in corpo
    assert "4321" not in corpo
    assert "9876" not in corpo
    for nome in ("raio", "latitude", "longitude", "centro", "rotulo", "prefixo"):
        assert nome not in corpo.lower()


def test_nome_com_acento_volta_igual(cliente, db):
    criar_campus("Ceilândia")
    criar_campus("Fazenda Água Limpa")

    resposta = cliente.get(ROTA)

    assert [c["nome"] for c in resposta.json()] == [
        "Ceilândia",
        "Fazenda Água Limpa",
    ]
    assert "Ceilândia" in resposta.content.decode("utf-8")


def test_tabela_vazia_devolve_200_com_lista_vazia_e_etag(cliente, db):
    resposta = cliente.get(ROTA)

    assert resposta.status_code == 200
    assert resposta.json() == []
    assert resposta["ETag"].startswith('"')


def test_quem_esta_logado_tambem_recebe_a_lista(cliente, campi, usuario):
    cliente.force_login(usuario)

    resposta = cliente.get(ROTA)

    assert resposta.status_code == 200
    assert resposta.json() == esperado(campi)


def test_uma_consulta_so_para_quem_nao_esta_logado(
    cliente, campi, django_assert_num_queries
):
    with django_assert_num_queries(1):
        resposta = cliente.get(ROTA)

    assert resposta.status_code == 200


# --- Cache e 304 -----------------------------------------------------------


def diretivas(resposta):
    return {d.strip() for d in resposta["Cache-Control"].split(",")}


def test_200_tem_etag_forte_e_cache_control_private_no_cache(cliente, campi):
    resposta = cliente.get(ROTA)

    etag = resposta["ETag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert not etag.startswith("W/")
    # SHA-256 em hexadecimal: 64 caracteres entre as aspas.
    assert len(etag) == 66
    assert diretivas(resposta) == {"private", "no-cache"}


def test_etag_e_o_sha256_do_json_publicado(cliente, campi):
    resposta = cliente.get(ROTA)

    corpo = json.dumps(
        esperado(campi), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert resposta["ETag"] == f'"{hashlib.sha256(corpo.encode()).hexdigest()}"'


def test_duas_requisicoes_seguidas_dao_o_mesmo_etag(cliente, campi):
    primeira = cliente.get(ROTA)
    segunda = cliente.get(ROTA)

    assert primeira["ETag"] == segunda["ETag"]


def test_if_none_match_igual_devolve_304_sem_corpo_com_cabecalhos(cliente, campi):
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag)

    assert resposta.status_code == 304
    assert resposta.content == b""
    assert resposta["ETag"] == etag
    assert diretivas(resposta) == {"private", "no-cache"}


def test_if_none_match_fraco_com_o_mesmo_valor_devolve_304(cliente, campi):
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=f"W/{etag}")

    assert resposta.status_code == 304
    assert resposta.content == b""


def test_if_none_match_diferente_devolve_200_com_corpo(cliente, campi):
    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH='"outro-valor"')

    assert resposta.status_code == 200
    assert resposta.json() == esperado(campi)


def test_mudar_um_nome_muda_o_etag(cliente, campi):
    etag_antigo = cliente.get(ROTA)["ETag"]
    Campus.objects.filter(pk=campi[0].pk).update(nome="Gama (FGA)")

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag_antigo)

    assert resposta.status_code == 200
    assert resposta["ETag"] != etag_antigo
    assert resposta.json()[0] == {"id": campi[0].id, "nome": "Gama (FGA)"}


def test_mudar_so_o_raio_e_as_coordenadas_nao_muda_o_etag(cliente, campi):
    etag = cliente.get(ROTA)["ETag"]
    Campus.objects.filter(pk=campi[0].pk).update(
        raio_confirmacao_metros=200,
        ru_latitude=Decimal("-15.000001"),
        ru_longitude=Decimal("-47.000001"),
        centro_latitude=Decimal("-15.000002"),
        centro_longitude=Decimal("-47.000002"),
        raio_deteccao_metros=2000,
    )

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag)

    assert resposta.status_code == 304
    assert resposta["ETag"] == etag


def test_head_com_if_none_match_igual_devolve_304(cliente, campi):
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.head(ROTA, HTTP_IF_NONE_MATCH=etag)

    assert resposta.status_code == 304
    assert resposta.content == b""
