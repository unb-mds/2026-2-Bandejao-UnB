"""Testes do AlertaEquipeService e do limite de e-mails (BE-12, ADR 0006).

Regra: cada alerta vira uma linha em ALERTA_LEITURA_CARDAPIO na hora.
O e-mail sai depois, um por campus no fim da execução (`enviar_pendentes`),
com todos os alertas ainda sem e-mail dos tipos que o limite deixa enviar:
no máximo 3 e-mails por dia e 6 horas entre dois envios, por campus e tipo.
Assim nenhum alerta fica sem e-mail para sempre (revisão do PR #218, itens 4
e 7). O dia é o de Brasília; o relógio é passado de fora (`agora`), e os
testes de fuso passam o mesmo instante em UTC, como o `timezone.now()` de
produção.
"""

import logging
import smtplib
from datetime import UTC, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command

from apps.cardapio.leitor.alerta_equipe_service import AlertaEquipeService
from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    ContadorAlerta,
    Refeicao,
    TipoAlerta,
)

BRASILIA = ZoneInfo("America/Sao_Paulo")
SEGUNDA_9H = datetime(2026, 11, 23, 9, 0, tzinfo=BRASILIA)
SEGUNDA = SEGUNDA_9H.date()
MEIA_NOITE = SEGUNDA_9H.replace(hour=0)
FALHA = TipoAlerta.FALHA_LEITURA_PDF
LEGENDA = TipoAlerta.LEGENDA_INVALIDA


@pytest.fixture
def gama(db):
    call_command("loaddata", "campi", verbosity=0)
    return Campus.objects.get(nome="Gama")


def _envio(campus, agora, *alertas):
    """Uma execução do Leitor no campus: registra os alertas e envia."""
    servico = AlertaEquipeService()
    for tipo, detalhe in alertas or [(FALHA, "download: HTTP 503")]:
        servico.registrar_alerta(tipo, campus, detalhe)
    return servico.enviar_pendentes(campus, agora=agora)


def _execucao(campus, agora, *alertas):
    """Quantos alertas foram no e-mail da execução."""
    envio = _envio(campus, agora, *alertas)
    assert envio.falhou is False
    return envio.enviados


def _contador(campus, tipo=FALHA, dia=SEGUNDA):
    return ContadorAlerta.objects.get(campus=campus, tipo=tipo, data=dia)


def test_constantes_do_c4():
    assert AlertaEquipeService.MAX_AVISOS_POR_DIA == 3
    assert timedelta(hours=6) == AlertaEquipeService.INTERVALO_MINIMO


# --------------------------------------------------------- registrar e enviar


def test_registrar_so_grava_a_linha_e_nao_envia(gama):
    alerta = AlertaEquipeService().registrar_alerta(FALHA, gama, "download: HTTP 503")
    assert AlertaLeituraCardapio.objects.get() == alerta
    assert (alerta.campus, alerta.tipo, alerta.refeicao, alerta.resolvido) == (
        gama,
        FALHA,
        None,
        False,
    )
    assert alerta.mensagem == "download: HTTP 503"
    assert alerta.email_enviado_em is None
    assert mail.outbox == []


def test_alerta_de_uma_refeicao_guarda_a_refeicao(gama):
    refeicao = Refeicao.objects.create(
        campus=gama,
        data=SEGUNDA,
        tipo="almoco",
        horario_inicio="11:00",
        horario_fim="14:30",
        fonte_pdf_url="https://ru.unb.br/wp-content/uploads/2026/11/Gama.pdf",
    )
    alerta = AlertaEquipeService().registrar_alerta(
        LEGENDA, gama, "legenda", refeicao=refeicao
    )
    assert alerta.refeicao == refeicao


def test_primeira_execucao_do_dia_envia_um_email_com_todos_os_alertas(gama, settings):
    settings.EMAIL_EQUIPE = "equipe@bandejaounb.com.br"
    enviados = _execucao(
        gama,
        SEGUNDA_9H,
        (FALHA, "Etapa: descoberta. Arquivo de outro campus."),
        (FALHA, "Etapa: cardápio não publicado."),
        (LEGENDA, "Etapa: marcadores. Legenda sem o ícone de mel."),
    )
    assert enviados == 3
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["equipe@bandejaounb.com.br"]
    assert "Gama" in email.subject and "3 alertas" in email.subject
    for trecho in ("outro campus", "não publicado", "ícone de mel"):
        assert trecho in email.body
    assert set(
        AlertaLeituraCardapio.objects.values_list("email_enviado_em", flat=True)
    ) == {SEGUNDA_9H}
    # Um e-mail com dois tipos conta para os dois contadores (ADR 0006).
    assert _contador(gama, FALHA).quantidade_enviada == 1
    assert _contador(gama, LEGENDA).quantidade_enviada == 1
    assert _contador(gama, FALHA).ultimo_envio_em == SEGUNDA_9H


def test_destinatario_vem_do_settings(gama, settings):
    settings.EMAIL_EQUIPE = "outra.equipe@exemplo.br"
    _execucao(gama, SEGUNDA_9H)
    assert mail.outbox[0].to == ["outra.equipe@exemplo.br"]


def test_sem_pendentes_nao_envia(gama):
    assert AlertaEquipeService().enviar_pendentes(gama, agora=SEGUNDA_9H) == (0, False)
    assert mail.outbox == []
    assert not ContadorAlerta.objects.exists()


def test_alerta_resolvido_nao_e_enviado(gama):
    AlertaEquipeService().registrar_alerta(FALHA, gama, "velho")
    AlertaLeituraCardapio.objects.update(resolvido=True)
    assert AlertaEquipeService().enviar_pendentes(gama, agora=SEGUNDA_9H) == (0, False)


# ------------------------------------------------------------------ limite


def test_alerta_preso_no_intervalo_sai_no_proximo_email(gama):
    # Item 4/7 da revisão: o "não publicado" que nasceu 1 h depois do
    # primeiro e-mail não se perde; vai junto no envio seguinte.
    _execucao(gama, SEGUNDA_9H, (FALHA, "Etapa: download."))
    assert (
        _execucao(
            gama, SEGUNDA_9H + timedelta(hours=1), (FALHA, "Etapa: não publicado.")
        )
        == 0
    )
    assert len(mail.outbox) == 1
    assert (
        _execucao(gama, SEGUNDA_9H + timedelta(hours=6), (FALHA, "Etapa: datas.")) == 2
    )
    assert len(mail.outbox) == 2
    assert "não publicado" in mail.outbox[1].body
    assert "datas" in mail.outbox[1].body
    assert not AlertaLeituraCardapio.objects.filter(email_enviado_em__isnull=True)


def test_seis_horas_e_o_minimo_entre_envios(gama):
    _execucao(gama, SEGUNDA_9H)
    _execucao(gama, SEGUNDA_9H + timedelta(hours=5, minutes=59))
    assert len(mail.outbox) == 1
    _execucao(gama, SEGUNDA_9H + timedelta(hours=6))
    assert len(mail.outbox) == 2
    contador = _contador(gama)
    assert contador.quantidade_enviada == 2
    assert contador.ultimo_envio_em == SEGUNDA_9H + timedelta(hours=6)


def test_quarta_tentativa_com_tres_envios_no_dia_nao_envia(gama):
    for horas in (0, 6, 12, 18):
        _execucao(gama, MEIA_NOITE + timedelta(hours=horas))
    assert len(mail.outbox) == 3
    assert _contador(gama).quantidade_enviada == 3
    # O 4º alerta continua pendente, para o dia seguinte.
    assert (
        AlertaLeituraCardapio.objects.filter(email_enviado_em__isnull=True).count() == 1
    )


def test_dia_seguinte_volta_a_enviar_e_leva_o_pendente(gama):
    for horas in (0, 6, 12, 18):
        _execucao(gama, MEIA_NOITE + timedelta(hours=horas))
    terca = MEIA_NOITE + timedelta(days=1, minutes=1)
    assert _execucao(gama, terca) == 2  # o de 18h de ontem e o de agora
    assert len(mail.outbox) == 4
    assert _contador(gama, dia=terca.date()).quantidade_enviada == 1
    assert _contador(gama).quantidade_enviada == 3


def test_intervalo_de_seis_horas_vale_tambem_na_virada_do_dia(gama):
    _execucao(gama, SEGUNDA_9H.replace(hour=23))
    _execucao(gama, SEGUNDA_9H.replace(hour=23) + timedelta(hours=2))
    assert len(mail.outbox) == 1


def test_tipo_preso_no_intervalo_nao_segura_o_outro_tipo(gama):
    _execucao(gama, SEGUNDA_9H, (FALHA, "Etapa: download."))
    enviados = _execucao(
        gama,
        SEGUNDA_9H + timedelta(hours=1),
        (FALHA, "Etapa: datas."),
        (LEGENDA, "Etapa: marcadores."),
    )
    assert enviados == 1
    assert "marcadores" in mail.outbox[1].body
    assert "datas" not in mail.outbox[1].body
    pendente = AlertaLeituraCardapio.objects.get(email_enviado_em__isnull=True)
    assert pendente.tipo == FALHA


def test_campi_diferentes_tem_contadores_separados(gama):
    darcy = Campus.objects.get(nome="Darcy Ribeiro")
    _execucao(gama, SEGUNDA_9H)
    _execucao(darcy, SEGUNDA_9H + timedelta(minutes=5))
    assert len(mail.outbox) == 2
    assert "Darcy Ribeiro" in mail.outbox[1].subject


def test_email_lista_no_maximo_vinte_alertas(gama):
    servico = AlertaEquipeService()
    for numero in range(25):
        servico.registrar_alerta(FALHA, gama, f"alerta número {numero:02d}")
    assert servico.enviar_pendentes(gama, agora=SEGUNDA_9H).enviados == 25
    corpo = mail.outbox[0].body
    # Os mais antigos primeiro: numa sequência longa de falhas, a causa
    # original aparece na lista (segunda revisão do PR #218).
    assert corpo.index("alerta número 00") < corpo.index("alerta número 19")
    assert "alerta número 20" not in corpo
    assert "e mais 5 alertas" in corpo


# ------------------------------------------------------------------- fuso


def test_dia_do_contador_e_o_de_brasilia_com_agora_em_utc(gama):
    # 01h UTC de terça ainda é segunda, 22h, em Brasília.
    _execucao(gama, datetime(2026, 11, 24, 1, 0, tzinfo=UTC))
    assert _contador(gama).data == SEGUNDA


def test_quarto_envio_as_21h30_de_brasilia_em_utc_nao_sai(gama):
    # 00h, 06h e 12h de segunda; às 21h30 de Brasília já é terça em UTC.
    for horas in (0, 6, 12):
        _execucao(gama, MEIA_NOITE + timedelta(hours=horas))
    _execucao(gama, (MEIA_NOITE + timedelta(hours=21, minutes=30)).astimezone(UTC))
    assert len(mail.outbox) == 3


def test_hora_do_email_e_a_de_brasilia(gama):
    _execucao(gama, datetime(2026, 11, 23, 15, 30, tzinfo=UTC))
    assert "23/11/2026 12:30" in mail.outbox[0].body


# ---------------------------------------------------------- zerar_contador


def test_zerar_contador_zera_a_quantidade_e_mantem_o_ultimo_envio(gama):
    darcy = Campus.objects.get(nome="Darcy Ribeiro")
    ontem = SEGUNDA_9H - timedelta(days=1)
    _execucao(gama, ontem)
    _execucao(gama, SEGUNDA_9H, (FALHA, "a"), (LEGENDA, "b"))
    _execucao(darcy, SEGUNDA_9H)
    AlertaEquipeService().zerar_contador(gama, agora=SEGUNDA_9H + timedelta(hours=3))
    assert _contador(gama, FALHA).quantidade_enviada == 0
    assert _contador(gama, LEGENDA).quantidade_enviada == 0
    assert _contador(gama, FALHA).ultimo_envio_em == SEGUNDA_9H
    assert _contador(gama, dia=ontem.date()).quantidade_enviada == 1
    assert _contador(darcy).quantidade_enviada == 1


def test_falha_intermitente_continua_respeitando_as_seis_horas(gama):
    # Revisão #218, item 5: falha, sucesso (zera), falha 3 h depois.
    _execucao(gama, SEGUNDA_9H)
    AlertaEquipeService().zerar_contador(gama, agora=SEGUNDA_9H + timedelta(hours=3))
    _execucao(gama, SEGUNDA_9H + timedelta(hours=3, minutes=1))
    assert len(mail.outbox) == 1


def test_depois_de_zerar_volta_a_ter_tres_envios_no_dia(gama):
    for horas in (0, 6, 12):
        _execucao(gama, MEIA_NOITE + timedelta(hours=horas))
    AlertaEquipeService().zerar_contador(gama, agora=MEIA_NOITE + timedelta(hours=15))
    _execucao(gama, MEIA_NOITE + timedelta(hours=18))
    assert len(mail.outbox) == 4
    assert _contador(gama).quantidade_enviada == 1


# -------------------------------------------------------- falha no envio


@pytest.mark.parametrize(
    "erro",
    [
        smtplib.SMTPServerDisconnected("caiu"),
        smtplib.SMTPRecipientsRefused({}),
        ConnectionRefusedError("rede"),
        TimeoutError("demorou"),
        # Revisão #218, item 6: configuração e cabeçalho também não podem
        # derrubar a leitura (ADR 0006).
        # Cabeçalho inválido: no Django 6.1 é ValueError (o BadHeaderError
        # está obsoleto).
        ValueError("Header values can't contain newlines"),
        ImproperlyConfigured("mailer"),
        UnicodeEncodeError("ascii", "ã", 0, 1, "sem acento"),
    ],
)
def test_falha_no_envio_nao_derruba_e_deixa_os_alertas_pendentes(gama, caplog, erro):
    with (
        mock.patch(
            "apps.cardapio.leitor.alerta_equipe_service.send_mail", side_effect=erro
        ),
        caplog.at_level(logging.ERROR),
    ):
        assert _envio(gama, SEGUNDA_9H) == (0, True)
    assert (
        AlertaLeituraCardapio.objects.filter(email_enviado_em__isnull=True).count() == 1
    )
    assert not ContadorAlerta.objects.filter(quantidade_enviada__gt=0).exists()
    assert type(erro).__name__ in caplog.text
    # Não contou como enviado: a próxima execução manda, sem esperar 6 h.
    assert _execucao(gama, SEGUNDA_9H + timedelta(hours=1)) == 2
    assert len(mail.outbox) == 1
    assert _contador(gama).quantidade_enviada == 1


def test_send_mail_que_nao_envia_nada_nao_conta_como_enviado(gama, caplog):
    # Segunda revisão #218, item B: com o destinatário descartado, o
    # `send_mail` devolve 0 sem levantar.
    with (
        mock.patch(
            "apps.cardapio.leitor.alerta_equipe_service.send_mail", return_value=0
        ),
        caplog.at_level(logging.ERROR),
    ):
        assert _envio(gama, SEGUNDA_9H) == (0, True)
    assert AlertaLeituraCardapio.objects.get().email_enviado_em is None
    assert not ContadorAlerta.objects.exists()
    assert "nenhum e-mail" in caplog.text


def test_log_da_falha_traz_o_codigo_smtp(gama, caplog):
    # Senha do Brevo trocada (535) e destinatário recusado (550) se separam
    # pelo código; nenhum dos dois traz dado de usuário.
    erro = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
    with (
        mock.patch(
            "apps.cardapio.leitor.alerta_equipe_service.send_mail", side_effect=erro
        ),
        caplog.at_level(logging.ERROR),
    ):
        _envio(gama, SEGUNDA_9H)
    assert "SMTPAuthenticationError" in caplog.text
    assert "535" in caplog.text


def test_email_nao_leva_dado_de_usuario(gama, usuario):
    _execucao(gama, SEGUNDA_9H)
    email = mail.outbox[0]
    for dado in (usuario.email_institucional, usuario.matricula_siape, usuario.apelido):
        assert dado not in email.body and dado not in email.subject


def test_corpo_do_email_nao_promete_o_que_nao_aconteceu(gama):
    # O "não publicado" não manteve cardápio nenhum: o texto fixo do e-mail
    # não pode dizer que manteve (revisão #218, documentação).
    _execucao(gama, SEGUNDA_9H, (FALHA, "Etapa: cardápio não publicado."))
    assert "foi mantido" not in mail.outbox[0].body
