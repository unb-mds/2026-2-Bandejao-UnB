"""Testes da LocalizacaoCampusConfig (BE-08, Exposição N4 4b).

Na v1 a config só lista os campi. O centro e o raio de detecção entram na
BE-E3 (extra 3).
"""

from decimal import Decimal

import pytest

from apps.cardapio.localizacao_campus_config import LocalizacaoCampusConfig
from apps.cardapio.models import Campus

pytestmark = pytest.mark.django_db


def criar_campus(nome, **kwargs):
    """Campus com todos os campos obrigatórios preenchidos."""
    dados = {
        "nome": nome,
        "ru_latitude": Decimal("-15.763100"),
        "ru_longitude": Decimal("-47.866900"),
        "raio_confirmacao_metros": 150,
        "centro_latitude": Decimal("-15.765000"),
        "centro_longitude": Decimal("-47.868000"),
        "raio_deteccao_metros": 1500,
    }
    dados.update(kwargs)
    # Colunas UNIQUE da BD-16 (ADR 0014): o nome, que já é único, serve.
    dados.setdefault("rotulo_pagina_ru", dados["nome"])
    dados.setdefault("prefixo_arquivo_pdf", dados["nome"])
    return Campus.objects.create(**dados)


def test_campi_devolve_todos_em_ordem_de_id():
    # Criados fora da ordem alfabética: a ordem tem que ser a do id.
    gama = criar_campus("Gama")
    darcy = criar_campus("Darcy Ribeiro")
    ceilandia = criar_campus("Ceilândia")

    campi = list(LocalizacaoCampusConfig.campi())

    assert [c.id for c in campi] == [gama.id, darcy.id, ceilandia.id]
    assert [c.nome for c in campi] == ["Gama", "Darcy Ribeiro", "Ceilândia"]


def test_campi_com_a_tabela_vazia_devolve_lista_vazia():
    assert list(LocalizacaoCampusConfig.campi()) == []
