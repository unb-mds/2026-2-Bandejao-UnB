"""BD-03: fixtures com os dados provisórios definidos pela equipe."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.cardapio.models import Campus, Marcador

pytestmark = pytest.mark.django_db

# Nome, latitude, longitude, raio em metros e confirmação ativa.
CAMPI_ESPERADOS = {
    1: ("Darcy Ribeiro", "-15.764203", "-47.870251", 150, True),
    2: ("Ceilândia", "-15.844288", "-48.099944", 150, True),
    3: ("Gama", "-15.989493", "-48.044024", 150, True),
    4: ("Planaltina", "-15.600701", "-47.659890", 150, True),
    5: ("Fazenda Água Limpa", "-15.940559", "-47.940424", 0, False),
}

MARCADORES_ESPERADOS = {
    "cogumelo",
    "leite_e_derivados",
    "mel",
    "pimenta",
    "soja",
    "trigo_gluten",
    "amendoim",
    "oleaginosa",
    "ovo",
    "suino",
}


def test_fixture_campi_carrega_cinco_campi_com_ids_fixos():
    assert not Campus.objects.exists()

    call_command("loaddata", "campi", verbosity=0)

    assert Campus.objects.count() == 5
    assert set(Campus.objects.values_list("pk", flat=True)) == set(CAMPI_ESPERADOS)

    for campus in Campus.objects.all():
        campus.full_clean()
        nome, latitude, longitude, raio, ativa = CAMPI_ESPERADOS[campus.pk]

        assert campus.nome == nome
        assert campus.ru_latitude == Decimal(latitude)
        assert campus.ru_longitude == Decimal(longitude)
        assert campus.raio_confirmacao_metros == raio
        assert campus.confirmacao_ativa is ativa

        # Valores provisórios do BD-03; serão revistos no BD-E3.
        assert campus.centro_latitude == campus.ru_latitude
        assert campus.centro_longitude == campus.ru_longitude
        assert campus.raio_deteccao_metros == raio

        for coordenada in (
            campus.ru_latitude,
            campus.ru_longitude,
            campus.centro_latitude,
            campus.centro_longitude,
        ):
            assert coordenada.as_tuple().exponent >= -6


def test_fixture_marcadores_carrega_os_dez_codigos_da_arquitetura():
    assert not Marcador.objects.exists()

    call_command("loaddata", "marcadores", verbosity=0)

    assert Marcador.objects.count() == 10
    assert set(Marcador.objects.values_list("nome", flat=True)) == MARCADORES_ESPERADOS

    for marcador in Marcador.objects.all():
        marcador.full_clean()


def test_recarregar_fixtures_preserva_ids_e_nao_duplica_registros():
    call_command("loaddata", "campi", "marcadores", verbosity=0)

    campi_antes = list(Campus.objects.order_by("pk").values())
    marcadores_antes = list(Marcador.objects.order_by("pk").values())

    call_command("loaddata", "campi", "marcadores", verbosity=0)

    assert Campus.objects.count() == 5
    assert Marcador.objects.count() == 10
    assert list(Campus.objects.order_by("pk").values()) == campi_antes
    assert list(Marcador.objects.order_by("pk").values()) == marcadores_antes
