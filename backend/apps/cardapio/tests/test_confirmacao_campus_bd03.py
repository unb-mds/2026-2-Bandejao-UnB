"""BD-03: invariantes dos raios e disponibilidade da confirmação."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.cardapio.models import Campus

pytestmark = pytest.mark.django_db

CONFIGURACOES_INVALIDAS = [
    pytest.param(True, 0, 150, id="ativa-com-raio-zero"),
    pytest.param(False, -1, 0, id="confirmacao-com-raio-negativo"),
    pytest.param(True, 150, -1, id="deteccao-negativa-com-confirmacao-ativa"),
    pytest.param(False, 0, -1, id="deteccao-negativa-com-confirmacao-desativada"),
]


def criar_campus(**ajustes):
    dados = {
        "nome": "Gama",
        "ru_latitude": Decimal("-15.989493"),
        "ru_longitude": Decimal("-48.044024"),
        "raio_confirmacao_metros": 150,
        "centro_latitude": Decimal("-15.989493"),
        "centro_longitude": Decimal("-48.044024"),
        "raio_deteccao_metros": 150,
    }
    dados.update(ajustes)
    # Colunas UNIQUE da BD-16 (ADR 0014): o nome, que já é único, serve.
    dados.setdefault("rotulo_pagina_ru", dados["nome"])
    dados.setdefault("prefixo_arquivo_pdf", dados["nome"])
    return Campus.objects.create(**dados)


def test_confirmacao_fica_ativa_por_padrao_ao_criar_campus():
    campus = criar_campus()

    campus.refresh_from_db()

    assert campus.confirmacao_ativa is True
    assert campus.raio_confirmacao_metros == 150


def test_permite_raio_positivo_minimo_com_confirmacao_ativa():
    campus = criar_campus(
        confirmacao_ativa=True,
        raio_confirmacao_metros=1,
    )

    campus.refresh_from_db()

    assert campus.confirmacao_ativa is True
    assert campus.raio_confirmacao_metros == 1


def test_permite_raios_zero_quando_confirmacao_esta_desativada():
    campus = criar_campus(
        confirmacao_ativa=False,
        raio_confirmacao_metros=0,
        raio_deteccao_metros=0,
    )

    campus.refresh_from_db()

    assert campus.confirmacao_ativa is False
    assert campus.raio_confirmacao_metros == 0
    assert campus.raio_deteccao_metros == 0


@pytest.mark.parametrize(
    ("ativa", "raio_confirmacao", "raio_deteccao"),
    CONFIGURACOES_INVALIDAS,
)
def test_banco_rejeita_criacao_com_configuracao_invalida(
    ativa,
    raio_confirmacao,
    raio_deteccao,
):
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_campus(
            confirmacao_ativa=ativa,
            raio_confirmacao_metros=raio_confirmacao,
            raio_deteccao_metros=raio_deteccao,
        )

    assert not Campus.objects.exists()


@pytest.mark.parametrize(
    ("ativa", "raio_confirmacao", "raio_deteccao"),
    CONFIGURACOES_INVALIDAS,
)
def test_banco_rejeita_atualizacao_com_configuracao_invalida(
    ativa,
    raio_confirmacao,
    raio_deteccao,
):
    campus = criar_campus()

    with pytest.raises(IntegrityError), transaction.atomic():
        Campus.objects.filter(pk=campus.pk).update(
            confirmacao_ativa=ativa,
            raio_confirmacao_metros=raio_confirmacao,
            raio_deteccao_metros=raio_deteccao,
        )

    campus.refresh_from_db()

    assert campus.confirmacao_ativa is True
    assert campus.raio_confirmacao_metros == 150
    assert campus.raio_deteccao_metros == 150
