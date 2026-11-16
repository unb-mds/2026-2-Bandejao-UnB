"""Fixtures do BD-03: dados de referência dos campi e marcadores."""

import pytest
from django.core.management import call_command

from apps.cardapio.models import Campus, Marcador

pytestmark = pytest.mark.django_db

CAMPI_ESPERADOS = {
    1: "Darcy Ribeiro",
    2: "Ceilândia",
    3: "Gama",
    4: "Planaltina",
    5: "Fazenda Água Limpa",
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
    assert dict(Campus.objects.values_list("pk", "nome")) == CAMPI_ESPERADOS

    for campus in Campus.objects.all():
        campus.full_clean()

        assert -90 <= campus.ru_latitude <= 90
        assert -180 <= campus.ru_longitude <= 180
        assert campus.raio_confirmacao_metros > 0

        assert campus.centro_latitude == campus.ru_latitude
        assert campus.centro_longitude == campus.ru_longitude
        assert campus.raio_deteccao_metros == campus.raio_confirmacao_metros

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

    campi_antes = list(Campus.objects.order_by("pk").values_list("pk", "nome"))
    marcadores_antes = list(Marcador.objects.order_by("pk").values_list("pk", "nome"))

    call_command("loaddata", "campi", "marcadores", verbosity=0)

    assert Campus.objects.count() == 5
    assert Marcador.objects.count() == 10
    assert list(Campus.objects.order_by("pk").values_list("pk", "nome")) == campi_antes
    assert (
        list(Marcador.objects.order_by("pk").values_list("pk", "nome"))
        == marcadores_antes
    )
