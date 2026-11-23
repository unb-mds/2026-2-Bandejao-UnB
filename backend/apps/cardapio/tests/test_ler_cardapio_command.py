"""Testes do comando `python manage.py ler_cardapio` (BE-12, C4 4a).

O cron do SO (BD-07) chama o comando de 3 em 3 horas. Ele lê o relógio uma
vez, processa os 5 campi, e a falha de um campus não impede os outros.
"""

import logging
import smtplib
from datetime import datetime
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import ManagementUtility, call_command
from django.core.management.base import CommandError
from django.db import DataError, OperationalError

from apps.cardapio.leitor.alerta_equipe_service import AlertaEquipeService
from apps.cardapio.leitor.cardapio_repository import CardapioRepository
from apps.cardapio.leitor.leitor_cardapio_service import LeitorCardapioService
from apps.cardapio.management.commands.ler_cardapio import LerCardapioCommand
from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    FonteCardapio,
    TipoAlerta,
)
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


def _darcy_quebra(erro):
    original = LeitorCardapioService.processar

    def processar(self, campus, agora):
        if campus.nome == "Darcy Ribeiro":
            raise erro
        return original(self, campus, agora)

    return mock.patch.object(LeitorCardapioService, "processar", processar)


def test_falha_inesperada_num_campus_nao_para_os_outros(campi, site, caplog):
    saida = StringIO()
    with (
        _darcy_quebra(RuntimeError("bug no Darcy")),
        caplog.at_level(logging.ERROR),
        mock.patch("django.utils.timezone.now", return_value=SABADO_10H),
        pytest.raises(CommandError, match="Darcy Ribeiro"),
    ):
        call_command("ler_cardapio", stdout=saida)

    gama = Campus.objects.get(nome="Gama")
    assert FonteCardapio.objects.filter(campus=gama).count() == 2
    # O resumo traz a mensagem da exceção, e não só o nome.
    assert "Darcy Ribeiro: erro inesperado (RuntimeError: bug no Darcy)" in (
        saida.getvalue()
    )
    assert "Gama: 2 lidas" in saida.getvalue()
    erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert any("RuntimeError" in r.getMessage() for r in erros)


def test_falha_inesperada_sai_com_codigo_diferente_de_zero(campi, site):
    # O cron (BD-07) só vê a falha pelo código de saída (revisão #218).
    with (
        _darcy_quebra(RuntimeError("bug no Darcy")),
        mock.patch("django.utils.timezone.now", return_value=SABADO_10H),
        pytest.raises(SystemExit) as saida,
    ):
        ManagementUtility(["manage.py", "ler_cardapio"]).execute()
    assert saida.value.code == 1


def test_falha_inesperada_do_campus_vira_alerta_da_equipe(campi, site):
    with (
        _darcy_quebra(RuntimeError("bug no Darcy")),
        pytest.raises(CommandError),
    ):
        _rodar()
    darcy = Campus.objects.get(nome="Darcy Ribeiro")
    [alerta] = AlertaLeituraCardapio.objects.filter(campus=darcy)
    assert alerta.tipo == TipoAlerta.FALHA_LEITURA_PDF
    assert "erro inesperado" in alerta.mensagem
    assert "RuntimeError: bug no Darcy" in alerta.mensagem


def test_alerta_do_erro_inesperado_falhando_nao_esconde_o_erro(campi, site, caplog):
    # Banco fora do ar: nem o alerta é gravado, mas o comando ainda sai com
    # erro e diz qual campus falhou.
    with (
        _darcy_quebra(OperationalError("banco fora do ar")),
        mock.patch.object(
            AlertaEquipeService,
            "registrar_alerta",
            side_effect=OperationalError("banco fora do ar"),
        ),
        caplog.at_level(logging.ERROR),
        pytest.raises(CommandError, match="Darcy Ribeiro"),
    ):
        _rodar()
    assert "alerta" in caplog.text.lower()


def test_erro_inesperado_em_todas_as_semanas_sai_com_codigo_diferente_de_zero(
    campi, site
):
    # Segunda revisão #218, item A: o serviço captura o erro da semana (para
    # alertar), mas o cron ainda precisa ver a falha pelo código de saída.
    saida = StringIO()
    with (
        mock.patch.object(
            CardapioRepository, "salvar", side_effect=DataError("Data too long")
        ),
        mock.patch("django.utils.timezone.now", return_value=SABADO_10H),
        pytest.raises(CommandError, match="erro inesperado") as erro,
    ):
        call_command("ler_cardapio", stdout=saida)
    # Os PDFs que estão nas fixtures falham ao gravar: Gama (2), Planaltina e
    # Fazenda (1 cada).
    assert "Gama" in str(erro.value) and "Fazenda Água Limpa" in str(erro.value)
    assert "Darcy Ribeiro" not in str(erro.value)
    assert "Gama: 0 lidas, 0 sem mudança, 2 alertas, 2 erros inesperados" in (
        saida.getvalue()
    )
    assert not FonteCardapio.objects.exists()


def test_email_de_alertas_que_falhou_sai_com_codigo_diferente_de_zero(
    campi, site, caplog
):
    # Recomendação da segunda revisão: senha do Brevo trocada deixaria os
    # alertas pendentes para sempre com o cron em código 0.
    erro = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
    saida = StringIO()
    with (
        mock.patch(
            "apps.cardapio.leitor.alerta_equipe_service.send_mail", side_effect=erro
        ),
        mock.patch("django.utils.timezone.now", return_value=SABADO_10H),
        caplog.at_level(logging.ERROR),
        pytest.raises(CommandError, match="e-mail") as falha,
    ):
        call_command("ler_cardapio", stdout=saida)
    assert "Darcy Ribeiro" in str(falha.value)
    assert "Darcy Ribeiro: 0 lidas, 0 sem mudança, 2 alertas, e-mail falhou" in (
        saida.getvalue()
    )
    # O Gama não teve alerta: não houve e-mail para falhar.
    assert "Gama: 2 lidas, 0 sem mudança, 0 alertas\n" in saida.getvalue()


def test_falha_no_envio_do_alerta_do_erro_inesperado_tem_log_proprio(
    campi, site, caplog
):
    with (
        _darcy_quebra(RuntimeError("bug no Darcy")),
        mock.patch.object(
            AlertaEquipeService,
            "enviar_pendentes",
            side_effect=OperationalError("banco fora do ar"),
        ),
        caplog.at_level(logging.ERROR),
        pytest.raises(CommandError),
    ):
        _rodar()
    darcy = Campus.objects.get(nome="Darcy Ribeiro")
    assert AlertaLeituraCardapio.objects.filter(campus=darcy).exists()
    assert "Não foi possível enviar o e-mail" in caplog.text


def test_execucao_sem_erro_inesperado_termina_com_codigo_zero(campi, site):
    # Falhas esperadas (404 nos PDFs que não estão nas fixtures) já são
    # alertas: não fazem o comando falhar.
    saida = _rodar()
    assert "Darcy Ribeiro: 0 lidas, 0 sem mudança, 2 alertas" in saida


def test_job_devolve_o_resultado_por_campus(campi, site):
    resultados = LerCardapioCommand().executar(SABADO_10H)
    por_nome = {campus.nome: r for campus, r in resultados}
    assert por_nome["Gama"].lidas == 2
    assert por_nome["Planaltina"].lidas == 1


def test_sem_campi_no_banco_nao_falha(db, site):
    saida = _rodar()
    assert "Nenhum campus" in saida
