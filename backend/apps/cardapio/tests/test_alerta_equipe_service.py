"""Testes do AlertaEquipeService e do limite de e-mails (BE-12, ADR 0006).

Regra: cada alerta vira uma linha em ALERTA_LEITURA_CARDAPIO; o e-mail à
equipe sai no máximo 3 vezes por dia e com 6 horas entre dois envios, por
campus e tipo. O dia é o de Brasília. O relógio é passado de fora (`agora`).
"""

import logging
import smtplib
from datetime import datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.management import call_command

from apps.cardapio.leitor.alerta_equipe_service import AlertaEquipeService
from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    ContadorAlerta,
    TipoAlerta,
)

BRASILIA = ZoneInfo("America/Sao_Paulo")
SEGUNDA_9H = datetime(2026, 11, 23, 9, 0, tzinfo=BRASILIA)
SEGUNDA = SEGUNDA_9H.date()
FALHA = TipoAlerta.FALHA_LEITURA_PDF
LEGENDA = TipoAlerta.LEGENDA_INVALIDA


@pytest.fixture
def gama(db):
    call_command("loaddata", "campi", verbosity=0)
    return Campus.objects.get(nome="Gama")


def _alertar(campus, agora, tipo=FALHA, detalhe="download: HTTP 503"):
    return AlertaEquipeService().registrar_alerta(tipo, campus, detalhe, agora=agora)


def _contador(campus, tipo=FALHA, dia=SEGUNDA):
    return ContadorAlerta.objects.get(campus=campus, tipo=tipo, data=dia)


def test_constantes_do_c4():
    assert AlertaEquipeService.MAX_AVISOS_POR_DIA == 3
    assert timedelta(hours=6) == AlertaEquipeService.INTERVALO_MINIMO


def test_primeira_falha_do_dia_grava_o_alerta_e_envia_o_email(gama, settings):
    settings.EMAIL_EQUIPE = "equipe@bandejaounb.com.br"
    alerta = _alertar(gama, SEGUNDA_9H)
    assert AlertaLeituraCardapio.objects.get() == alerta
    assert (alerta.campus, alerta.tipo, alerta.refeicao, alerta.resolvido) == (
        gama,
        FALHA,
        None,
        False,
    )
    assert "download: HTTP 503" in alerta.mensagem
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["equipe@bandejaounb.com.br"]
    assert "Gama" in email.subject
    assert "download: HTTP 503" in email.body
    contador = _contador(gama)
    assert (contador.quantidade_enviada, contador.ultimo_envio_em) == (1, SEGUNDA_9H)


def test_destinatario_vem_do_settings(gama, settings):
    settings.EMAIL_EQUIPE = "outra.equipe@exemplo.br"
    _alertar(gama, SEGUNDA_9H)
    assert mail.outbox[0].to == ["outra.equipe@exemplo.br"]


def test_segunda_falha_uma_hora_depois_grava_sem_email(gama):
    _alertar(gama, SEGUNDA_9H)
    _alertar(gama, SEGUNDA_9H + timedelta(hours=1))
    assert AlertaLeituraCardapio.objects.count() == 2
    assert len(mail.outbox) == 1
    assert _contador(gama).quantidade_enviada == 1


def test_falha_seis_horas_depois_envia_de_novo(gama):
    _alertar(gama, SEGUNDA_9H)
    _alertar(gama, SEGUNDA_9H + timedelta(hours=5, minutes=59))
    _alertar(gama, SEGUNDA_9H + timedelta(hours=6))
    assert len(mail.outbox) == 2
    contador = _contador(gama)
    assert contador.quantidade_enviada == 2
    assert contador.ultimo_envio_em == SEGUNDA_9H + timedelta(hours=6)


def test_quarta_tentativa_com_tres_envios_no_dia_nao_envia(gama):
    # 00h, 06h, 12h e 18h: as três primeiras enviam, a quarta não.
    meia_noite = SEGUNDA_9H.replace(hour=0)
    for horas in (0, 6, 12, 18):
        _alertar(gama, meia_noite + timedelta(hours=horas))
    assert len(mail.outbox) == 3
    assert AlertaLeituraCardapio.objects.count() == 4
    assert _contador(gama).quantidade_enviada == 3


def test_dia_seguinte_volta_a_enviar_com_contador_novo(gama):
    meia_noite = SEGUNDA_9H.replace(hour=0)
    for horas in (0, 6, 12, 18):
        _alertar(gama, meia_noite + timedelta(hours=horas))
    # Terça, 00h01 em Brasília: 6h01 depois do último envio, dia novo.
    terca = meia_noite + timedelta(days=1, minutes=1)
    _alertar(gama, terca)
    assert len(mail.outbox) == 4
    assert _contador(gama, dia=terca.date()).quantidade_enviada == 1
    assert _contador(gama).quantidade_enviada == 3


def test_intervalo_de_seis_horas_vale_tambem_na_virada_do_dia(gama):
    # Segunda 23h e terça 01h: dia novo, mas só 2 h depois do último e-mail.
    _alertar(gama, SEGUNDA_9H.replace(hour=23))
    _alertar(gama, SEGUNDA_9H.replace(hour=23) + timedelta(hours=2))
    assert len(mail.outbox) == 1


def test_dia_do_contador_e_o_de_brasilia(gama):
    # 01h UTC de terça ainda é segunda, 22h, em Brasília.
    _alertar(gama, datetime(2026, 11, 24, 1, 0, tzinfo=ZoneInfo("UTC")))
    assert _contador(gama).data == SEGUNDA_9H.date()


def test_tipos_diferentes_no_mesmo_campus_tem_contadores_separados(gama):
    _alertar(gama, SEGUNDA_9H, tipo=FALHA)
    _alertar(gama, SEGUNDA_9H + timedelta(minutes=5), tipo=LEGENDA)
    assert len(mail.outbox) == 2
    assert _contador(gama, FALHA).quantidade_enviada == 1
    assert _contador(gama, LEGENDA).quantidade_enviada == 1


def test_campi_diferentes_tem_contadores_separados(gama):
    darcy = Campus.objects.get(nome="Darcy Ribeiro")
    _alertar(gama, SEGUNDA_9H)
    _alertar(darcy, SEGUNDA_9H + timedelta(minutes=5))
    assert len(mail.outbox) == 2


def test_alerta_de_uma_refeicao_guarda_a_refeicao(gama):
    from apps.cardapio.models import Refeicao

    refeicao = Refeicao.objects.create(
        campus=gama,
        data=SEGUNDA_9H.date(),
        tipo="almoco",
        horario_inicio="11:00",
        horario_fim="14:30",
        fonte_pdf_url="https://ru.unb.br/wp-content/uploads/2026/11/Gama.pdf",
    )
    alerta = AlertaEquipeService().registrar_alerta(
        LEGENDA, gama, "legenda", refeicao=refeicao, agora=SEGUNDA_9H
    )
    assert alerta.refeicao == refeicao


@pytest.mark.parametrize(
    "erro",
    [
        smtplib.SMTPServerDisconnected("caiu"),
        smtplib.SMTPRecipientsRefused({}),
        ConnectionRefusedError("rede"),
        TimeoutError("demorou"),
    ],
)
def test_falha_no_envio_nao_derruba_e_nao_conta_como_enviado(gama, caplog, erro):
    with (
        mock.patch(
            "apps.cardapio.leitor.alerta_equipe_service.send_mail", side_effect=erro
        ),
        caplog.at_level(logging.ERROR),
    ):
        alerta = _alertar(gama, SEGUNDA_9H)
    # O alerta fica gravado para a equipe consultar (ADR 0006).
    assert AlertaLeituraCardapio.objects.filter(pk=alerta.pk).exists()
    assert not ContadorAlerta.objects.filter(quantidade_enviada__gt=0).exists()
    assert type(erro).__name__ in caplog.text
    # Como não contou, a próxima execução tenta de novo, sem esperar 6 h.
    _alertar(gama, SEGUNDA_9H + timedelta(hours=1))
    assert len(mail.outbox) == 1
    assert _contador(gama).quantidade_enviada == 1


def test_zerar_contador_apaga_as_linhas_do_dia_do_campus(gama):
    darcy = Campus.objects.get(nome="Darcy Ribeiro")
    ontem = SEGUNDA_9H - timedelta(days=1)
    _alertar(gama, ontem)
    _alertar(gama, SEGUNDA_9H, tipo=FALHA)
    _alertar(gama, SEGUNDA_9H, tipo=LEGENDA)
    _alertar(darcy, SEGUNDA_9H)
    AlertaEquipeService().zerar_contador(gama, agora=SEGUNDA_9H + timedelta(hours=3))
    assert sorted(ContadorAlerta.objects.values_list("campus__nome", "data")) == [
        ("Darcy Ribeiro", SEGUNDA_9H.date()),
        ("Gama", ontem.date()),
    ]
    # Os alertas em si ficam (histórico da equipe).
    assert AlertaLeituraCardapio.objects.count() == 4


def test_depois_de_zerar_a_mesma_falha_envia_de_novo(gama):
    _alertar(gama, SEGUNDA_9H)
    AlertaEquipeService().zerar_contador(gama, agora=SEGUNDA_9H + timedelta(hours=1))
    _alertar(gama, SEGUNDA_9H + timedelta(hours=2))
    assert len(mail.outbox) == 2


def test_email_nao_leva_dado_de_usuario(gama, usuario):
    _alertar(gama, SEGUNDA_9H)
    email = mail.outbox[0]
    for dado in (usuario.email_institucional, usuario.matricula_siape, usuario.apelido):
        assert dado not in email.body and dado not in email.subject
