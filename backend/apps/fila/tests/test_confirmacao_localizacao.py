"""Distância ao RU e confirmação da localização (BE-09, RF12, Fila N4 4a)."""

import pytest

from apps.fila.confirmacao_localizacao_service import ConfirmacaoLocalizacaoService
from apps.fila.distancia_geografica import Coordenadas, DistanciaGeografica
from apps.fila.erros import LocalizacaoNaoConfirmadaError
from apps.fila.localizacao_ru_config import LocalizacaoRUConfig
from apps.fila.tests.apoio import RAIO, RU_DARCY, RU_GAMA, ao_norte, criar_campus

# --- DistanciaGeografica -----------------------------------------------------


def test_distancia_de_um_ponto_a_ele_mesmo_e_zero():
    assert DistanciaGeografica().metros(RU_DARCY, RU_DARCY) == 0


def test_distancia_para_o_norte_e_a_andada():
    assert DistanciaGeografica().metros(RU_DARCY, ao_norte(RU_DARCY, 150)) == (
        pytest.approx(150, abs=0.01)
    )


def test_distancia_e_simetrica():
    distancia = DistanciaGeografica()
    assert distancia.metros(RU_DARCY, RU_GAMA) == distancia.metros(RU_GAMA, RU_DARCY)


def test_distancia_entre_os_rus_do_darcy_e_do_gama():
    """Cerca de 31 km em linha reta: muito além de qualquer raio.

    Conferido pela aproximação plana: 25,05 km no sentido norte-sul e
    18,59 km no leste-oeste.
    """
    assert DistanciaGeografica().metros(RU_DARCY, RU_GAMA) == pytest.approx(
        31_190, rel=0.01
    )


def test_coordenadas_nao_aparecem_no_repr():
    """RI09: um log ou traceback com o objeto não mostra a posição."""
    texto = repr(Coordenadas(latitude=-15.123456, longitude=-47.654321))
    assert "15.123456" not in texto
    assert "47.654321" not in texto


# --- LocalizacaoRUConfig -----------------------------------------------------


@pytest.mark.django_db
def test_config_le_centro_raio_e_disponibilidade_do_campus():
    campus = criar_campus()

    assert LocalizacaoRUConfig.confirmacao_ativa(campus) is True
    assert LocalizacaoRUConfig.centro(campus) == RU_DARCY
    assert LocalizacaoRUConfig.raio_metros(campus) == RAIO


# --- ConfirmacaoLocalizacaoService -------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("metros", [0, 80, RAIO - 0.5])
def test_dentro_do_raio_confirma(metros):
    campus = criar_campus()

    assert (
        ConfirmacaoLocalizacaoService().confirmar(campus, ao_norte(RU_DARCY, metros))
        is None
    )


@pytest.mark.django_db
def test_na_borda_do_raio_confirma(monkeypatch):
    """O raio é inclusivo: exatamente na borda ainda conta como dentro.

    A distância é fixada para o teste não depender do arredondamento do float.
    """
    campus = criar_campus()
    monkeypatch.setattr(DistanciaGeografica, "metros", lambda *_: float(RAIO))

    ConfirmacaoLocalizacaoService().confirmar(campus, RU_DARCY)


@pytest.mark.django_db
def test_um_milimetro_alem_da_borda_nao_confirma(monkeypatch):
    campus = criar_campus()
    monkeypatch.setattr(DistanciaGeografica, "metros", lambda *_: RAIO + 0.001)

    with pytest.raises(LocalizacaoNaoConfirmadaError):
        ConfirmacaoLocalizacaoService().confirmar(campus, RU_DARCY)


@pytest.mark.django_db
@pytest.mark.parametrize("metros", [RAIO + 0.5, 500])
def test_fora_do_raio_nao_confirma(metros):
    campus = criar_campus()

    with pytest.raises(LocalizacaoNaoConfirmadaError):
        ConfirmacaoLocalizacaoService().confirmar(campus, ao_norte(RU_DARCY, metros))


@pytest.mark.django_db
def test_no_ru_de_outro_campus_nao_confirma():
    """Estar no RU do Gama não confirma o check-in no Darcy Ribeiro (RN09)."""
    darcy = criar_campus()
    criar_campus(nome="Gama", ru=RU_GAMA)

    with pytest.raises(LocalizacaoNaoConfirmadaError):
        ConfirmacaoLocalizacaoService().confirmar(darcy, RU_GAMA)


@pytest.mark.django_db
def test_confirmacao_desativada_nao_confirma_nem_no_ru():
    """BD-03: raio zero com a confirmação desligada nunca autoriza."""
    campus = criar_campus(raio=0, ativa=False)

    with pytest.raises(LocalizacaoNaoConfirmadaError):
        ConfirmacaoLocalizacaoService().confirmar(campus, RU_DARCY)


@pytest.mark.django_db
def test_confirmacao_desativada_nao_calcula_a_distancia(monkeypatch):
    """A disponibilidade é lida antes da distância (contrato do BD-03)."""
    campus = criar_campus(raio=0, ativa=False)

    def nao_deve_calcular(*_):
        raise AssertionError("calculou a distância com a confirmação desativada")

    monkeypatch.setattr(DistanciaGeografica, "metros", nao_deve_calcular)
    with pytest.raises(LocalizacaoNaoConfirmadaError):
        ConfirmacaoLocalizacaoService().confirmar(campus, RU_DARCY)
