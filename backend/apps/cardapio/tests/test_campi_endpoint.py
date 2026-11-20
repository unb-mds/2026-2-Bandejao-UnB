"""GET /api/campi/ (BE-08, RF07.2, RI09, Exposição N4 4b).

A lista é pública e só tem `id` e `nome`. O raio de confirmação do RU e as
coordenadas nunca saem (RI09). A resposta vai com `ETag` e
`Cache-Control: private, no-cache`, e o servidor responde 304 sem corpo
quando o `If-None-Match` bate. As decisões estão nas notas do diagrama 4b
(docs/arquitetura/backend/c4-nivel-4-exposicao-cardapio.md) e, com a
discussão, na #98.

Os campi usam valores marcantes no raio e nas coordenadas, para dar para
procurar esses números no corpo da resposta.
"""

import hashlib
import logging
import re
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

# ETag forte: só o valor entre aspas, sem o prefixo W/.
FORMATO_ETAG_FORTE = re.compile(r'^"[^"]+"$')


def criar_campus(nome, **kwargs):
    """Campus com todos os campos obrigatórios e os valores marcantes."""
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
    # Colunas UNIQUE da BD-16 (ADR 0014): o nome, que já é único, serve.
    dados.setdefault("rotulo_pagina_ru", dados["nome"])
    dados.setdefault("prefixo_arquivo_pdf", dados["nome"])
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


def diretivas(resposta):
    return {d.strip() for d in resposta["Cache-Control"].split(",")}


# --- Resposta pública ------------------------------------------------------


def test_sem_login_devolve_200_com_id_e_nome_em_ordem_de_id(cliente, campi):
    resposta = cliente.get(ROTA)

    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "application/json"
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
    # Também os dígitos de cada valor, sem o sinal e o ponto. Os ids e nomes
    # deste teste (1 a 3, Gama, Darcy, Ceilândia) não têm essas sequências.
    for digitos in ("765432", "876543", "712345", "898765", "4321", "9876"):
        assert digitos not in corpo
    # Nomes de coluna que não podem virar chave. `rotulo` e `prefixo` são as
    # colunas da BD-16 (ADR 0014), internas do Leitor, que também não saem.
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
    assert FORMATO_ETAG_FORTE.match(resposta["ETag"])
    assert diretivas(resposta) == {"private", "no-cache"}


def test_tabela_vazia_vai_para_o_log(cliente, db, caplog):
    # Vazia quer dizer deploy sem o loaddata da BD-03: sem o log, o PWA só
    # mostraria "nenhum campus" e nada levaria à causa.
    with caplog.at_level(logging.WARNING, logger="apps.cardapio.views"):
        cliente.get(ROTA)

    mensagens = [r.getMessage() for r in caplog.records]
    assert any("CAMPUS vazia" in m for m in mensagens)


def test_com_campi_nao_vai_nada_para_o_log(cliente, campi, caplog):
    with caplog.at_level(logging.DEBUG, logger="apps.cardapio.views"):
        cliente.get(ROTA)

    assert caplog.records == []


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


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_metodos_de_escrita_dao_405_sem_gravar_nada(cliente, campi, metodo):
    # A rota é AllowAny: o IsAuthenticated padrão não protegeria uma escrita
    # acrescentada aqui no futuro.
    antes = Campus.objects.count()

    resposta = getattr(cliente, metodo)(ROTA, {"nome": "Novo"}, format="json")

    assert resposta.status_code == 405
    assert Campus.objects.count() == antes


# --- Cache e 304 -----------------------------------------------------------


def test_200_tem_etag_forte_e_cache_control_private_no_cache(cliente, campi):
    resposta = cliente.get(ROTA)

    assert FORMATO_ETAG_FORTE.match(resposta["ETag"])
    assert diretivas(resposta) == {"private", "no-cache"}


def test_etag_e_o_sha256_dos_bytes_do_corpo(cliente, campi):
    # O ETag é forte, então tem que mudar com qualquer byte do corpo.
    resposta = cliente.get(ROTA)

    digest = hashlib.sha256(resposta.content).hexdigest()
    assert resposta["ETag"] == f'"{digest}"'


def test_etag_e_o_mesmo_com_outro_cliente_e_os_mesmos_dados(campi):
    # Determinístico entre processos e clientes (pegaria um hash() do Python).
    primeira = APIClient().get(ROTA)
    segunda = APIClient().get(ROTA)

    assert primeira["ETag"] == segunda["ETag"]


def test_accept_com_indent_nao_muda_o_corpo_nem_o_etag(cliente, campi):
    # Corpo e ETag saem sempre dos mesmos bytes: um indent pedido no Accept
    # não pode gerar um corpo diferente com o mesmo ETag forte.
    normal = cliente.get(ROTA)
    com_indent = cliente.get(ROTA, HTTP_ACCEPT="application/json; indent=4")

    assert com_indent.content == normal.content
    assert com_indent["ETag"] == normal["ETag"]


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


def test_if_none_match_com_lista_que_contem_o_etag_devolve_304(cliente, campi):
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=f'"outro", {etag}')

    assert resposta.status_code == 304


def test_if_none_match_com_lista_sem_o_etag_devolve_200(cliente, campi):
    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH='"um", W/"dois"')

    assert resposta.status_code == 200
    assert resposta.json() == esperado(campi)


@pytest.mark.parametrize("com_campi", [True, False])
def test_if_none_match_asterisco_devolve_304(cliente, db, com_campi):
    if com_campi:
        criar_campus("Gama")

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH="*")

    assert resposta.status_code == 304
    assert resposta.content == b""


def test_if_none_match_diferente_devolve_200_com_corpo(cliente, campi):
    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH='"outro-valor"')

    assert resposta.status_code == 200
    assert resposta.json() == esperado(campi)


@pytest.mark.parametrize(
    "cabecalho",
    [
        {"HTTP_IF_UNMODIFIED_SINCE": "Sun, 15 Nov 2026 12:00:00 GMT"},
        {"HTTP_IF_MATCH": '"outro-valor"'},
        {"HTTP_IF_MATCH": "*"},
        {"HTTP_IF_MODIFIED_SINCE": "Sun, 15 Nov 2026 12:00:00 GMT"},
    ],
)
def test_outras_condicoes_sao_ignoradas_e_devolvem_200(cliente, campi, cabecalho):
    # Só o If-None-Match é tratado. As outras condições não podem virar um
    # 412 cru, fora do contrato, que faria o seletor de campus sumir.
    resposta = cliente.get(ROTA, **cabecalho)

    assert resposta.status_code == 200
    assert resposta.json() == esperado(campi)


def test_mudar_um_nome_muda_o_etag(cliente, campi):
    etag_antigo = cliente.get(ROTA)["ETag"]
    Campus.objects.filter(pk=campi[0].pk).update(nome="Gama (FGA)")

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag_antigo)

    assert resposta.status_code == 200
    assert resposta["ETag"] != etag_antigo
    assert resposta.json()[0] == {"id": campi[0].id, "nome": "Gama (FGA)"}


def test_incluir_um_campus_muda_o_etag(cliente, campi):
    etag_antigo = cliente.get(ROTA)["ETag"]
    novo = criar_campus("Planaltina")

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag_antigo)

    assert resposta.status_code == 200
    assert resposta["ETag"] != etag_antigo
    assert resposta.json()[-1] == {"id": novo.id, "nome": "Planaltina"}


def test_remover_um_campus_muda_o_etag(cliente, campi):
    etag_antigo = cliente.get(ROTA)["ETag"]
    campi[1].delete()

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag_antigo)

    assert resposta.status_code == 200
    assert resposta["ETag"] != etag_antigo
    assert resposta.json() == esperado([campi[0], campi[2]])


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


def test_head_sem_if_none_match_devolve_200_com_cabecalhos(cliente, campi):
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.head(ROTA)

    assert resposta.status_code == 200
    assert resposta["ETag"] == etag
    assert diretivas(resposta) == {"private", "no-cache"}


def test_head_com_if_none_match_igual_devolve_304(cliente, campi):
    # O test client sempre tira o corpo do HEAD; o que prova é o status e o
    # ETag.
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.head(ROTA, HTTP_IF_NONE_MATCH=etag)

    assert resposta.status_code == 304
    assert resposta["ETag"] == etag


# --- Quem está logado (o caso que justifica o `private`) ---------------------


def test_logado_recebe_set_cookie_e_private_no_200(cliente, campi, usuario):
    cliente.force_login(usuario)

    resposta = cliente.get(ROTA)

    assert "sessionid" in resposta.cookies
    assert diretivas(resposta) == {"private", "no-cache"}


def test_logado_recebe_set_cookie_e_private_no_304(cliente, campi, usuario):
    cliente.force_login(usuario)
    etag = cliente.get(ROTA)["ETag"]

    resposta = cliente.get(ROTA, HTTP_IF_NONE_MATCH=etag)

    assert resposta.status_code == 304
    assert "sessionid" in resposta.cookies
    assert diretivas(resposta) == {"private", "no-cache"}


def test_etag_do_logado_e_igual_ao_do_anonimo(campi, usuario):
    anonimo = APIClient().get(ROTA)
    logado_cliente = APIClient()
    logado_cliente.force_login(usuario)
    logado = logado_cliente.get(ROTA)

    assert logado["ETag"] == anonimo["ETag"]
