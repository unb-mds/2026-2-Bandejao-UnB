"""Ponta a ponta: página e PDFs reais do RU -> ler_cardapio -> GET /api/cardapio/.

Junta o Leitor (BE-12) e a Exposição (BE-11): o que o Leitor grava tem que
sair na API do jeito que a BE-11 lê (publicado = existe a `FonteCardapio`
da semana). Só a rede (`SiteDoRUFalso`) e o relógio são simulados.
Valores esperados: os da imagem do almoço do Gama de 16/11.
"""

from datetime import datetime
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pdfplumber
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.cardapio.models import Campus
from apps.cardapio.tests.apoio_leitor import URL_GAMA_23, SiteDoRUFalso

BRASILIA = ZoneInfo("America/Sao_Paulo")
ROTA = "/api/cardapio/"


@pytest.fixture
def gama(db):
    call_command("loaddata", "campi", "marcadores", verbosity=0)
    return Campus.objects.get(nome="Gama")


@pytest.fixture
def site():
    with SiteDoRUFalso() as falso:
        yield falso


def _ler_cardapio(quando):
    with mock.patch("django.utils.timezone.now", return_value=quando):
        call_command("ler_cardapio", stdout=StringIO())


def _pedir(quando, **parametros):
    with mock.patch("django.utils.timezone.now", return_value=quando):
        return APIClient().get(ROTA, parametros)


def _categorias(corpo):
    return {
        c["nome"]: [(p["descricao"], sorted(p["marcadores"])) for p in c["pratos"]]
        for c in corpo["categorias"]
    }


QUINTA_19_12H = datetime(2026, 11, 19, 12, 0, tzinfo=BRASILIA)
SABADO_21_10H = datetime(2026, 11, 21, 10, 0, tzinfo=BRASILIA)


def test_semana_lida_sai_publicada_com_pratos_e_marcadores(gama, site):
    _ler_cardapio(SABADO_21_10H)

    resposta = _pedir(QUINTA_19_12H, campus=gama.pk)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["status"], corpo["refeicao"], corpo["data"]) == (
        "publicado",
        "almoco",
        "2026-11-19",
    )
    assert corpo["alergenosIndisponivel"] is False
    categorias = _categorias(corpo)
    assert list(categorias)[:3] == ["SALADA 1", "SALADA 2", "MOLHO PARA SALADA"]
    assert categorias["SOBREMESA"] == [
        ("Mix de doces", ["amendoim", "leite_e_derivados"]),
        ("Fruta", []),
    ]
    assert categorias["PRATO PRINCIPAL VEGETARIANO ESTRITO"] == [
        ("Soja xadrez", ["amendoim", "soja"])
    ]


def test_filtros_da_be11_funcionam_com_o_que_o_leitor_gravou(gama, site):
    _ler_cardapio(SABADO_21_10H)

    corpo = _pedir(
        QUINTA_19_12H,
        campus=gama.pk,
        dieta="vegetariano_estrito",
        marcadores="amendoim",
    ).json()

    nomes = [c["nome"] for c in corpo["categorias"]]
    # A dieta copiada para os pratos (Prato.dieta) tira as outras linhas.
    assert "PRATO PRINCIPAL PADRÃO" not in nomes
    assert "PRATO PRINCIPAL OVOLACTOVEGETARIANO" not in nomes
    sinalizados = {
        p["descricao"]
        for c in corpo["categorias"]
        for p in c["pratos"]
        if p["contemMarcadorSelecionado"]
    }
    assert sinalizados == {"Mix de doces", "Soja xadrez"}


def test_pdf_recusado_sem_semana_anterior_sai_nao_publicado(gama, site):
    site.conteudos[URL_GAMA_23] = b"%PDF-1.7 corrompido"
    _ler_cardapio(SABADO_21_10H)

    terca = datetime(2026, 11, 24, 12, 0, tzinfo=BRASILIA)
    corpo = _pedir(terca, campus=gama.pk).json()
    assert corpo["status"] == "nao_publicado"
    assert corpo["categorias"] == []
    # A semana de 16/11, lida com sucesso, continua publicada.
    assert _pedir(QUINTA_19_12H, campus=gama.pk).json()["status"] == "publicado"


def test_pagina_so_em_texto_sai_com_o_filtro_de_marcador_desativado(
    gama, site, monkeypatch
):
    # Um ícone a mais, fora das células, na página do almoço.
    original = pdfplumber.page.Page.images

    def images(self):
        imagens = original.fget(self)
        if type(self) is not pdfplumber.page.Page or self.page_number != 2:
            return imagens
        icone = next(im for im in imagens if 150 < im["top"] < 450 and im["x0"] > 180)
        largura = icone["x1"] - icone["x0"]
        return [*imagens, {**icone, "x0": 100, "x1": 100 + largura}]

    monkeypatch.setattr(pdfplumber.page.Page, "images", property(images))
    _ler_cardapio(SABADO_21_10H)

    corpo = _pedir(QUINTA_19_12H, campus=gama.pk, marcadores="amendoim").json()
    assert corpo["status"] == "publicado"
    assert corpo["alergenosIndisponivel"] is True
    assert corpo["filtroMarcadorDesativado"] is True
    assert _categorias(corpo)["SOBREMESA"] == [("Mix de doces", []), ("Fruta", [])]
