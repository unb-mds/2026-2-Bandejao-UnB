"""Testes do comando `python manage.py ler_cardapio` (BE-12, C4 4a).

O cron do SO (BD-07) chama o comando de 3 em 3 horas. Ele lê o relógio uma
vez, processa os 5 campi, e a falha de um campus não impede os outros.
"""

import logging
from datetime import datetime
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from apps.cardapio.leitor.leitor_cardapio_service import LeitorCardapioService
from apps.cardapio.management.commands.ler_cardapio import LerCardapioCommand
from apps.cardapio.models import Campus, FonteCardapio
from apps.cardapio.tests.apoio_leitor import SiteDoRUFalso

BRASILIA = ZoneInfo("America/Sao_Paulo")
SABADO_10H = datetime(2026, 11, 21, 10, 0, tzinfo=BRASILIA)


@pytest.fixture
def campi(db):
    call_command("loaddata", "campi", "marcadores", verbosity=0)


@pytest.fixture
def site():
    with SiteDoRUFalso() as falso:
        yield falso


def _rodar():
    saida = StringIO()
    with mock.patch("django.utils.timezone.now", return_value=SABADO_10H):
        call_command("ler_cardapio", stdout=saida)
    return saida.getvalue()


def test_comando_processa_os_cinco_campi_com_um_relogio_so(campi, site):
    agoras = []
    original = LeitorCardapioService.processar

    def espiar(self, campus, agora):
        agoras.append((campus.nome, agora))
        return original(self, campus, agora)

    with mock.patch.object(LeitorCardapioService, "processar", espiar):
        saida = _rodar()

    assert [nome for nome, _ in agoras] == [
        "Darcy Ribeiro",
        "Ceilândia",
        "Gama",
        "Planaltina",
        "Fazenda Água Limpa",
    ]
    # O mesmo `agora` (lido uma vez pelo comando) para todos os campi.
    assert {agora for _, agora in agoras} == {SABADO_10H}
    # Os PDFs que estão nas fixtures foram lidos: Gama (2), Planaltina (23/11)
    # e Fazenda (16/11). Os outros respondem 404 e viram alerta.
    assert FonteCardapio.objects.count() == 4
    assert "Gama: 2 lidas, 0 sem mudança, 0 alertas" in saida
    assert "Darcy Ribeiro: 0 lidas, 0 sem mudança, 2 alertas" in saida
    # A página do RU é pedida uma vez na execução, não uma por campus.
    paginas = [u for u in site.pedidos if "cardapio-refeitorio" in u]
    assert paginas == ["https://ru.unb.br/cardapio-refeitorio/"]


def test_falha_inesperada_num_campus_nao_para_os_outros(campi, site, caplog):
    original = LeitorCardapioService.processar

    def darcy_quebra(self, campus, agora):
        if campus.nome == "Darcy Ribeiro":
            raise RuntimeError("bug no Darcy")
        return original(self, campus, agora)

    with (
        mock.patch.object(LeitorCardapioService, "processar", darcy_quebra),
        caplog.at_level(logging.ERROR),
    ):
        saida = _rodar()

    gama = Campus.objects.get(nome="Gama")
    assert FonteCardapio.objects.filter(campus=gama).count() == 2
    assert "Darcy Ribeiro: erro inesperado (RuntimeError)" in saida
    assert "Gama: 2 lidas" in saida
    erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert any("RuntimeError" in r.getMessage() for r in erros)


def test_job_devolve_o_resultado_por_campus(campi, site):
    resultados = LerCardapioCommand().executar(SABADO_10H)
    por_nome = {campus.nome: r for campus, r in resultados}
    assert por_nome["Gama"].lidas == 2
    assert por_nome["Planaltina"].lidas == 1


def test_sem_campi_no_banco_nao_falha(db, site):
    saida = _rodar()
    assert "Nenhum campus" in saida
