"""Testes do LeitorCardapioService, o orquestrador do Leitor (BE-12, C4 4a/4c).

Tudo de verdade (descoberta, parser, banco, alertas), menos a rede e o
e-mail: o site do RU é o `SiteDoRUFalso` (HTML e PDFs reais das fixtures) e
o e-mail vai para o `mail.outbox`. O relógio (`agora`) é fixo, no horário
de Brasília. Os casos seguem a seção 9.1 do guia da BE-12 e a linha da L15
do plano de testes.

Semana vigente no relógio padrão (sábado, 21/11/2026): 16 a 22/11.
"""

import hashlib
import logging
from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pdfplumber
import pytest
import requests
from django.core import mail
from django.core.management import call_command
from django.db import DatabaseError, DataError

from apps.avaliacao.models import Avaliacao
from apps.cardapio.leitor import cardapio_pdf_parser as parser
from apps.cardapio.leitor.cardapio_downloader import CardapioDownloader
from apps.cardapio.leitor.cardapio_repository import CardapioRepository
from apps.cardapio.leitor.leitor_cardapio_service import LeitorCardapioService
from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    ContadorAlerta,
    FonteCardapio,
    Prato,
    PratoMarcador,
    Refeicao,
    StatusLeitura,
    TipoAlerta,
)
from apps.cardapio.tests.apoio_leitor import (
    LINK_16,
    LINK_23,
    URL_FAZENDA_16,
    URL_GAMA_16,
    URL_GAMA_23,
    SiteDoRUFalso,
    pdf,
)

BRASILIA = ZoneInfo("America/Sao_Paulo")
SABADO_10H = datetime(2026, 11, 21, 10, 0, tzinfo=BRASILIA)
SEGUNDA_16 = date(2026, 11, 16)
SEGUNDA_23 = date(2026, 11, 23)
FALHA = TipoAlerta.FALHA_LEITURA_PDF


@pytest.fixture
def gama(db):
    call_command("loaddata", "campi", "marcadores", verbosity=0)
    return Campus.objects.get(nome="Gama")


@pytest.fixture
def site():
    with SiteDoRUFalso() as falso:
        yield falso


def _processar(campus, agora=SABADO_10H):
    return LeitorCardapioService().processar(campus, agora)


def _alertas(campus):
    return list(
        AlertaLeituraCardapio.objects.filter(campus=campus)
        .order_by("id")
        .values_list("tipo", "mensagem")
    )


def _datas(campus, semana_inicio):
    return sorted(
        set(
            Refeicao.objects.filter(
                campus=campus,
                data__gte=semana_inicio,
                data__lte=semana_inicio + timedelta(days=6),
            ).values_list("data", flat=True)
        )
    )


def _espiar_parser():
    """Conta as leituras do PDF sem mudar o que o parser faz."""
    return mock.patch.object(
        parser.CardapioPDFParser,
        "extrair",
        autospec=True,
        side_effect=parser.CardapioPDFParser.extrair,
    )


# ------------------------------------------------------- leitura com sucesso


def test_primeira_execucao_grava_as_duas_semanas_e_a_fonte(gama, site):
    resultado = _processar(gama)

    assert (resultado.lidas, resultado.sem_mudanca, resultado.alertas) == (2, 0, 0)
    # Gama: 5 dias num link de 7 é aceito (o PDF só traz os dias com RU).
    assert _datas(gama, SEGUNDA_16) == [date(2026, 11, d) for d in range(16, 21)]
    assert _datas(gama, SEGUNDA_23)[0] == SEGUNDA_23
    fontes = {f.semana_inicio: f for f in FonteCardapio.objects.filter(campus=gama)}
    assert set(fontes) == {SEGUNDA_16, SEGUNDA_23}
    assert fontes[SEGUNDA_16].url == URL_GAMA_16
    assert (
        fontes[SEGUNDA_16].sha256
        == hashlib.sha256(pdf("Gama-Semana-01-16-11-a-20-11-1.pdf")).hexdigest()
    )
    assert fontes[SEGUNDA_16].verificado_em == SABADO_10H
    assert fontes[SEGUNDA_16].processado_em == SABADO_10H
    assert _alertas(gama) == []
    assert mail.outbox == []


def test_semana_gravada_com_marcadores_e_refeicoes_com_status_ok(gama, site):
    _processar(gama)
    sobremesa = Prato.objects.filter(
        categoria__refeicao__campus=gama,
        categoria__refeicao__data=date(2026, 11, 19),
        categoria__refeicao__tipo="almoco",
        categoria__nome="SOBREMESA",
    ).order_by("ordem")
    assert [(p.nome, {m.nome for m in p.marcadores.all()}) for p in sobremesa] == [
        ("Mix de doces", {"leite_e_derivados", "amendoim"}),
        ("Fruta", set()),
    ]
    assert set(Refeicao.objects.values_list("status_leitura", flat=True)) == {
        StatusLeitura.OK
    }
    assert set(Refeicao.objects.values_list("fonte_pdf_url", flat=True)) == {
        URL_GAMA_16,
        URL_GAMA_23,
    }


def test_mesma_url_e_mesmo_sha256_nao_le_o_pdf_de_novo(gama, site):
    _processar(gama)
    lidas_em = dict(Refeicao.objects.values_list("pk", "lida_em"))
    depois = SABADO_10H + timedelta(hours=3)

    with _espiar_parser() as extrair:
        resultado = _processar(gama, depois)

    assert extrair.call_count == 0
    assert (resultado.lidas, resultado.sem_mudanca) == (0, 2)
    for fonte in FonteCardapio.objects.all():
        assert fonte.verificado_em == depois
        assert fonte.processado_em == SABADO_10H
    assert dict(Refeicao.objects.values_list("pk", "lida_em")) == lidas_em


def test_sha256_diferente_na_mesma_url_le_de_novo_e_atualiza(gama, site, usuario):
    _processar(gama)
    jantar_sexta = Refeicao.objects.get(
        campus=gama, data=date(2026, 11, 20), tipo="jantar"
    )
    jantar_quinta = Refeicao.objects.get(
        campus=gama, data=date(2026, 11, 19), tipo="jantar"
    )
    Avaliacao.objects.create(usuario=usuario, refeicao=jantar_quinta, nota=4)
    # O RU troca o arquivo sem mudar o nome: o PDF novo não tem jantar.
    site.conteudos[URL_GAMA_16] = pdf("Fazenda-Semana-01-16-11-a-20-11-2.pdf")
    depois = SABADO_10H + timedelta(hours=3)

    with _espiar_parser() as extrair:
        resultado = _processar(gama, depois)

    assert extrair.call_count == 1
    assert resultado.lidas == 1
    fonte = FonteCardapio.objects.get(campus=gama, semana_inicio=SEGUNDA_16)
    assert (
        fonte.sha256
        == hashlib.sha256(pdf("Fazenda-Semana-01-16-11-a-20-11-2.pdf")).hexdigest()
    )
    assert fonte.processado_em == depois
    # P1: o jantar sem avaliação some; o que tem avaliação fica.
    assert not Refeicao.objects.filter(pk=jantar_sexta.pk).exists()
    assert Refeicao.objects.filter(pk=jantar_quinta.pk).exists()
    assert Avaliacao.objects.filter(refeicao=jantar_quinta).count() == 1


def test_execucao_sem_alerta_zera_o_contador_do_campus(gama, site):
    ContadorAlerta.objects.create(
        campus=gama,
        tipo=FALHA,
        data=SABADO_10H.date(),
        quantidade_enviada=2,
        ultimo_envio_em=SABADO_10H - timedelta(hours=7),
    )
    _processar(gama)
    assert not ContadorAlerta.objects.filter(campus=gama).exists()


# ---------------------------------------------- falhas que mantêm o último


def _estado():
    return {
        "refeicoes": sorted(
            Refeicao.objects.values_list("pk", "data", "tipo", "lida_em")
        ),
        "fontes": sorted(
            FonteCardapio.objects.values_list(
                "semana_inicio", "url", "sha256", "processado_em"
            )
        ),
        "pratos": Prato.objects.count(),
        "marcadores": PratoMarcador.objects.count(),
    }


def _ja_lido(gama):
    _processar(gama)
    return _estado()


def test_dia_do_pdf_fora_do_intervalo_do_link_mantem_o_ultimo_e_alerta(gama, site):
    antes = _ja_lido(gama)
    # A semana de 23/11 passa a apontar para um PDF da semana de 16/11.
    site.conteudos[URL_GAMA_23] = pdf("Gama-Semana-01-16-11-a-20-11-1.pdf")

    resultado = _processar(gama, SABADO_10H + timedelta(hours=3))

    assert _estado() == antes
    assert resultado.alertas == 1
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA
    assert "datas" in mensagem
    assert "23/11/2026" in mensagem and URL_GAMA_23 in mensagem
    assert "16/11/2026" in mensagem  # o dia fora do intervalo


def test_pdf_sem_paginas_nao_apaga_a_semana_ja_lida(gama, site):
    # Revisão #218, item 3: sem refeição nenhuma, o PDF é recusado; antes,
    # o remover_ausentes apagava a semana e o SHA novo era gravado.
    antes = _ja_lido(gama)
    ContadorAlerta.objects.create(
        campus=gama, tipo=FALHA, data=SABADO_10H.date(), quantidade_enviada=1
    )
    site.conteudos[URL_GAMA_16] = pdf("pdf-sem-paginas.pdf")

    resultado = _processar(gama, SABADO_10H + timedelta(hours=3))

    assert _estado() == antes
    assert resultado.lidas == 0
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA and "nenhuma refeição" in mensagem
    assert ContadorAlerta.objects.filter(campus=gama, tipo=FALHA).exists()


def test_pdf_recusado_sem_semana_anterior_nao_cria_linha(gama, site):
    site.conteudos[URL_GAMA_23] = b"%PDF-1.7 corrompido"
    _processar(gama)
    assert _datas(gama, SEGUNDA_23) == []
    assert not FonteCardapio.objects.filter(semana_inicio=SEGUNDA_23).exists()
    # P2: nenhuma linha `leitura_falhou`.
    assert not Refeicao.objects.filter(status_leitura=StatusLeitura.LEITURA_FALHOU)
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA and "formato" in mensagem.lower()
    assert "sem cardápio anterior" in mensagem
    # A outra semana foi lida normalmente.
    assert _datas(gama, SEGUNDA_16)


def test_pdf_recusado_com_semana_anterior_diz_que_manteve(gama, site):
    _processar(gama)
    site.conteudos[URL_GAMA_23] = b"<html>erro</html>"
    _processar(gama, SABADO_10H + timedelta(hours=3))
    [(_, mensagem)] = _alertas(gama)
    assert "último cardápio válido mantido" in mensagem.lower()


def test_download_error_mantem_o_ultimo_e_segue_para_a_outra_semana(gama, site):
    antes = _ja_lido(gama)
    site.conteudos[URL_GAMA_23] = 500
    site.conteudos[URL_GAMA_16] = pdf("Fazenda-Semana-01-16-11-a-20-11-2.pdf")

    resultado = _processar(gama, SABADO_10H + timedelta(hours=3))

    assert resultado.lidas == 1
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA
    assert "download" in mensagem.lower() and "HTTP 500" in mensagem
    fonte_23 = FonteCardapio.objects.get(semana_inicio=SEGUNDA_23)
    assert (fonte_23.url, fonte_23.processado_em) == next(
        (url, proc) for s, url, _, proc in antes["fontes"] if s == SEGUNDA_23
    )
    # O link foi achado: verificado_em anda mesmo com a falha do download.
    assert fonte_23.verificado_em == SABADO_10H + timedelta(hours=3)


def test_titulo_ausente_alerta_e_nao_baixa_nada(gama, site):
    site.trocar_no_html("Cardápio Gama</h3>", "Cardápio Gamma</h3>")
    resultado = _processar(gama)
    assert resultado.alertas == 1
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA
    assert "descoberta" in mensagem.lower() and "ausente" in mensagem
    assert site.pedidos == ["https://ru.unb.br/cardapio-refeitorio/"]
    assert not Refeicao.objects.exists()


def test_pagina_fora_do_ar_alerta_uma_vez_mesmo_depois_do_prazo(gama):
    # Segunda, 30/11, 13h: a semana vigente não está na página, mas a
    # descoberta falhou para o campus inteiro: não sai o "não publicado".
    with mock.patch(
        "apps.cardapio.leitor.cardapio_downloader.requests.get",
        side_effect=requests.ConnectionError("fora do ar"),
    ):
        _processar(gama, datetime(2026, 11, 30, 13, 0, tzinfo=BRASILIA))
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA and "página do RU" in mensagem


def test_link_reprovado_alerta_e_nao_e_baixado(gama, site):
    site.trocar_no_html(URL_GAMA_23, URL_GAMA_23.replace("Gama-", "Planaltina-"))
    _processar(gama)
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA and "descoberta" in mensagem.lower()
    assert "Planaltina-Semana-02" in mensagem
    assert URL_GAMA_23.replace("Gama-", "Planaltina-") not in site.pedidos


def test_erro_no_meio_da_gravacao_nao_grava_nada_da_semana(gama, site, caplog):
    with (
        mock.patch.object(
            CardapioRepository,
            "remover_ausentes",
            side_effect=DatabaseError("caiu no meio"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        resultado = _processar(gama)
    assert not Refeicao.objects.exists()
    assert not FonteCardapio.objects.exists()
    # Revisão #218, item 2: o erro inesperado vira alerta da semana (com o
    # traceback no log) e não derruba o campus.
    assert resultado.alertas == 2
    mensagens = [m for _, m in _alertas(gama)]
    assert all("erro inesperado" in m and "DatabaseError" in m for m in mensagens)
    assert "caiu no meio" in mensagens[0]
    assert "Traceback" in caplog.text


def _salvar_falha_na_semana(inicio, erro):
    """Faz o `salvar` falhar só nas páginas do PDF da semana `inicio`."""
    original = CardapioRepository.salvar

    def salvar(self, campus, fonte, refeicao):
        if fonte.inicio == inicio:
            raise erro
        return original(self, campus, fonte, refeicao)

    return mock.patch.object(CardapioRepository, "salvar", salvar)


def test_erro_inesperado_numa_semana_nao_impede_a_outra(gama, site):
    # Ex.: DataError do MySQL estrito com um prato de mais de 200 caracteres.
    with _salvar_falha_na_semana(SEGUNDA_23, DataError("Data too long")):
        resultado = _processar(gama, datetime(2026, 11, 30, 13, 0, tzinfo=BRASILIA))
    assert resultado.lidas == 1
    assert _datas(gama, SEGUNDA_16)
    assert _datas(gama, SEGUNDA_23) == []
    mensagens = [m for _, m in _alertas(gama)]
    assert any("erro inesperado" in m and "Data too long" in m for m in mensagens)
    # A semana falhou, mas o resto do processar rodou: o "não publicado" da
    # semana de 30/11 também saiu.
    assert any("não publicado" in m for m in mensagens)


def test_erro_inesperado_na_descoberta_vira_alerta(gama, site):
    with mock.patch.object(
        CardapioDownloader, "_blocos_por_titulo", side_effect=AttributeError("bs4")
    ):
        resultado = _processar(gama)
    assert resultado.alertas == 1
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA
    assert "erro inesperado" in mensagem and "AttributeError" in mensagem


def test_rollback_da_releitura_devolve_a_semana_anterior_inteira(gama, site):
    antes = _ja_lido(gama)
    urls = sorted(Refeicao.objects.values_list("pk", "fonte_pdf_url"))
    marcadores = sorted(
        PratoMarcador.objects.values_list(
            "prato__categoria__refeicao_id", "prato__nome", "marcador__nome"
        )
    )
    # O PDF da semana de 16/11 muda, e a gravação falha na 2ª página.
    site.conteudos[URL_GAMA_16] = pdf("Fazenda-Semana-01-16-11-a-20-11-2.pdf")
    original = CardapioRepository.salvar
    chamadas = []

    def salvar(self, campus, fonte, refeicao):
        chamadas.append(refeicao.refeicao)
        if len(chamadas) == 2:
            raise DatabaseError("falhou na 2ª refeição")
        return original(self, campus, fonte, refeicao)

    with mock.patch.object(CardapioRepository, "salvar", salvar):
        _processar(gama, SABADO_10H + timedelta(hours=3))

    assert _estado() == antes  # inclui o SHA e o processado_em antigos
    assert sorted(Refeicao.objects.values_list("pk", "fonte_pdf_url")) == urls
    assert (
        sorted(
            PratoMarcador.objects.values_list(
                "prato__categoria__refeicao_id", "prato__nome", "marcador__nome"
            )
        )
        == marcadores
    )


# ------------------------------------------------------ página só em texto


def _icone_solto_no_almoco(monkeypatch):
    """Um ícone a mais, na coluna das categorias da página 2 (almoço):
    `AssociacaoFalhouError` só nessa página (caso do teste do BE-04)."""
    original = pdfplumber.page.Page.images

    def images(self):
        imagens = original.fget(self)
        if type(self) is not pdfplumber.page.Page or self.page_number != 2:
            return imagens
        icone = next(im for im in imagens if 150 < im["top"] < 450 and im["x0"] > 180)
        largura = icone["x1"] - icone["x0"]
        return [*imagens, {**icone, "x0": 100, "x1": 100 + largura}]

    monkeypatch.setattr(pdfplumber.page.Page, "images", property(images))


def test_pagina_so_em_texto_grava_sem_marcadores_e_alerta(gama, site, monkeypatch):
    _icone_solto_no_almoco(monkeypatch)
    site.conteudos[URL_GAMA_23] = 404
    resultado = _processar(gama)

    almocos = Refeicao.objects.filter(campus=gama, tipo="almoco", data__lt=SEGUNDA_23)
    assert set(almocos.values_list("status_leitura", flat=True)) == {
        StatusLeitura.ALERGENOS_INDISPONIVEIS
    }
    assert not PratoMarcador.objects.filter(prato__categoria__refeicao__in=almocos)
    # Os pratos estão lá, só sem marcadores.
    assert Prato.objects.filter(categoria__refeicao__in=almocos).count() > 40
    outras = Refeicao.objects.filter(campus=gama).exclude(tipo="almoco")
    assert set(outras.values_list("status_leitura", flat=True)) == {StatusLeitura.OK}
    assert PratoMarcador.objects.filter(prato__categoria__refeicao__in=outras)

    alertas = AlertaLeituraCardapio.objects.filter(tipo=TipoAlerta.ASSOCIACAO_FALHOU)
    [alerta] = alertas
    assert alerta.refeicao == almocos.get(data=SEGUNDA_16)
    assert "almoco" in alerta.mensagem or "almoço" in alerta.mensagem
    assert "fora das células" in alerta.mensagem
    # A semana conta como lida com sucesso (RF06.3): tem FonteCardapio.
    assert FonteCardapio.objects.filter(semana_inicio=SEGUNDA_16).exists()
    assert resultado.alertas == 2  # este e o 404 da outra semana


def test_legenda_invalida_gera_alerta_do_tipo_legenda(gama, site, monkeypatch):
    original = parser.normalizar
    monkeypatch.setattr(
        parser,
        "normalizar",
        lambda texto: "pimenta" if original(texto) == "mel" else original(texto),
    )
    site.conteudos[URL_GAMA_23] = 404
    _processar(gama)
    tipos = [t for t, _ in _alertas(gama)]
    # Uma linha por página (café, almoço e jantar) e uma do 404.
    assert sorted(tipos) == sorted([FALHA] + [TipoAlerta.LEGENDA_INVALIDA] * 3)
    assert set(
        Refeicao.objects.filter(data__lt=SEGUNDA_23).values_list(
            "status_leitura", flat=True
        )
    ) == {StatusLeitura.ALERGENOS_INDISPONIVEIS}


def test_mesmo_pdf_so_em_texto_nao_repete_o_alerta(gama, site, monkeypatch):
    _icone_solto_no_almoco(monkeypatch)
    _processar(gama)
    _processar(gama, SABADO_10H + timedelta(hours=3))
    assert (
        AlertaLeituraCardapio.objects.filter(tipo=TipoAlerta.ASSOCIACAO_FALHOU).count()
        == 2
    )  # uma por semana, só na primeira execução


# ------------------------------------------------- não publicado e contador


SEGUNDA_30_13H = datetime(2026, 11, 30, 13, 0, tzinfo=BRASILIA)


def test_vigente_ausente_depois_de_segunda_12h_alerta_nao_publicado(gama, site):
    # Em 30/11 a página ainda só tem as semanas de 16 e 23/11.
    resultado = _processar(gama, SEGUNDA_30_13H)
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA
    assert "não publicado" in mensagem
    assert "30/11/2026" in mensagem
    assert resultado.alertas == 1
    assert len(mail.outbox) == 1


def test_nao_publicado_por_varias_execucoes_nao_zera_o_contador(gama, site):
    for horas in (0, 3, 6, 9):
        _processar(gama, SEGUNDA_30_13H + timedelta(hours=horas))
    assert len(_alertas(gama)) == 4
    contador = ContadorAlerta.objects.get(campus=gama, tipo=FALHA)
    # 13h e 19h: o intervalo de 6 h segura os outros; o contador não zerou.
    assert contador.quantidade_enviada == 2
    assert len(mail.outbox) == 2


def test_vigente_ausente_antes_de_segunda_12h_nao_alerta(gama, site):
    ContadorAlerta.objects.create(
        campus=gama, tipo=FALHA, data=date(2026, 11, 30), quantidade_enviada=1
    )
    _processar(gama, datetime(2026, 11, 30, 11, 59, tzinfo=BRASILIA))
    assert _alertas(gama) == []
    assert not ContadorAlerta.objects.exists()


def test_vigente_ausente_exatamente_na_segunda_12h_ja_alerta(gama, site):
    # O prazo do Anexo A é "a partir de segunda, 12h": 12h00 já conta.
    _processar(gama, datetime(2026, 11, 30, 12, 0, tzinfo=BRASILIA))
    [(_, mensagem)] = _alertas(gama)
    assert "não publicado" in mensagem


def test_link_sem_datas_alerta_com_o_texto_do_link(gama, site):
    site.trocar_no_html(LINK_23, "ISM &#8211; Semana 2", 3)
    _processar(gama)
    [(tipo, mensagem)] = _alertas(gama)
    assert tipo == FALHA
    assert "link 'ISM – Semana 2'" in mensagem
    assert "datas legíveis" in mensagem


def test_domingo_conta_na_semana_da_segunda_anterior(gama, site):
    # Domingo, 29/11: a semana vigente é a de 23/11, que está na página.
    _processar(gama, datetime(2026, 11, 29, 20, 0, tzinfo=BRASILIA))
    assert _alertas(gama) == []


def test_vigente_presente_com_pdf_falhando_so_alerta_a_falha(gama, site):
    site.conteudos[URL_GAMA_23] = 503
    _processar(gama, datetime(2026, 11, 24, 15, 0, tzinfo=BRASILIA))
    [(_tipo, mensagem)] = _alertas(gama)
    assert "HTTP 503" in mensagem
    assert "não publicado" not in mensagem


def test_vigente_com_link_reprovado_nao_e_nao_publicado(gama, site):
    # O link da semana vigente existe, mas é de outro campus: conta como
    # presente para o "não publicado" (ADR 0014); sai só o alerta da descoberta.
    site.trocar_no_html(URL_GAMA_23, URL_GAMA_23.replace("Gama-", "Darcy-Ribeiro-"))
    _processar(gama, datetime(2026, 11, 24, 15, 0, tzinfo=BRASILIA))
    [(_, mensagem)] = _alertas(gama)
    assert "não publicado" not in mensagem


def test_vigente_com_dois_links_nao_e_nao_publicado(gama, site):
    site.trocar_no_html(LINK_16, LINK_23, 3)  # o 3º é o do Gama
    _processar(gama, datetime(2026, 11, 24, 15, 0, tzinfo=BRASILIA))
    mensagens = [m for _, m in _alertas(gama)]
    assert len(mensagens) == 2
    assert all("mesma semana" in m for m in mensagens)


def test_semana_seguinte_lida_e_vigente_com_falha_nao_zera(gama, site):
    ContadorAlerta.objects.create(
        campus=gama,
        tipo=FALHA,
        data=SABADO_10H.date(),
        quantidade_enviada=1,
        ultimo_envio_em=SABADO_10H - timedelta(hours=1),
    )
    site.conteudos[URL_GAMA_16] = 500  # vigente falha
    resultado = _processar(gama)
    assert resultado.lidas == 1  # a seguinte (23/11) foi lida
    contador = ContadorAlerta.objects.get(campus=gama, tipo=FALHA)
    assert contador.quantidade_enviada == 1  # não zerou e não enviou (1 h)
    assert mail.outbox == []


def test_alerta_so_em_texto_tambem_impede_zerar(gama, site, monkeypatch):
    ContadorAlerta.objects.create(
        campus=gama, tipo=FALHA, data=SABADO_10H.date(), quantidade_enviada=1
    )
    _icone_solto_no_almoco(monkeypatch)
    _processar(gama)
    assert ContadorAlerta.objects.filter(campus=gama, tipo=FALHA).exists()


def test_falha_no_email_nao_derruba_a_leitura(gama, site, caplog):
    site.conteudos[URL_GAMA_23] = 500
    with (
        mock.patch(
            "apps.cardapio.leitor.alerta_equipe_service.send_mail",
            side_effect=ConnectionRefusedError("smtp"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        resultado = _processar(gama)
    assert resultado.lidas == 1
    assert _datas(gama, SEGUNDA_16)
    assert len(_alertas(gama)) == 1
    assert "ConnectionRefusedError" in caplog.text


def test_mensagens_nao_levam_dado_de_usuario(gama, site, usuario):
    site.conteudos[URL_GAMA_23] = 500
    _processar(gama, SEGUNDA_30_13H)
    for _, mensagem in _alertas(gama):
        assert usuario.email_institucional not in mensagem
        assert usuario.matricula_siape not in mensagem


def test_fazenda_16_11_e_lida_com_a_semana_de_23_ausente(db, site):
    call_command("loaddata", "campi", "marcadores", verbosity=0)
    fazenda = Campus.objects.get(nome="Fazenda Água Limpa")
    resultado = _processar(fazenda)
    assert resultado.lidas == 1
    tipos = set(Refeicao.objects.filter(campus=fazenda).values_list("tipo", flat=True))
    assert tipos == {"cafe", "almoco"}
    assert FonteCardapio.objects.get(campus=fazenda).url == URL_FAZENDA_16
    # O PDF da Fazenda de 23/11 não está nas fixtures: 404, alerta de download.
    [(_, mensagem)] = _alertas(fazenda)
    assert "HTTP 404" in mensagem
