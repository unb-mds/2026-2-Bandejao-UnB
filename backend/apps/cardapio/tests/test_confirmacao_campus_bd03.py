"""BD-03: configuração da disponibilidade da confirmação por campus."""

from decimal import Decimal

import pytest

from apps.cardapio.models import Campus

pytestmark = pytest.mark.django_db


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
    return Campus.objects.create(**dados)


def test_confirmacao_fica_ativa_por_padrao_para_campi_existentes():
    campus = criar_campus()

    campus.refresh_from_db()

    assert campus.confirmacao_ativa is True
    assert campus.raio_confirmacao_metros == 150


def test_permite_gravar_fal_com_confirmacao_desativada():
    campus = criar_campus(
        nome="Fazenda Água Limpa",
        ru_latitude=Decimal("-15.940559"),
        ru_longitude=Decimal("-47.940424"),
        raio_confirmacao_metros=0,
        centro_latitude=Decimal("-15.940559"),
        centro_longitude=Decimal("-47.940424"),
        raio_deteccao_metros=0,
        confirmacao_ativa=False,
    )

    campus.full_clean()
    campus.refresh_from_db()

    assert campus.confirmacao_ativa is False
    assert campus.raio_confirmacao_metros == 0
    assert campus.raio_deteccao_metros == 0
