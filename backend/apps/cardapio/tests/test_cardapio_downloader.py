"""Testes da descoberta do PDF de cada campus na página do RU (BE-12, ADR 0014).

Teste de caracterização da L15 (plano de testes, seção 5): o HTML real da
página `cardapio-refeitorio`, salvo em 21/11/2026, é a fixture. As variações
(blocos em outra ordem, título ausente ou repetido, link de outro campus...)
são geradas no próprio teste a partir dele, com o BeautifulSoup.

Nenhuma requisição de verdade: o `requests.get` do módulo é simulado.
Os campi vêm da fixture `campi.json` (BD-03), sem banco: o Downloader só lê
o rótulo e o prefixo de cada um.
"""

import hashlib
import json
from datetime import date
from pathlib import Path
from unittest import mock

import pytest
import requests
from bs4 import BeautifulSoup

from apps.cardapio.leitor.cardapio_downloader import (
    ArquivoPDF,
    CardapioDownloader,
    FontePDF,
)
from apps.cardapio.leitor.cardapio_pdf_parser import (
    DownloadError,
    FonteNaoEncontradaError,
    FormatoPDFInvalidoError,
)
from apps.cardapio.leitor.fonte_cardapio_config import FonteCardapioConfig
from apps.cardapio.models import Campus
from apps.cardapio.tests.apoio_leitor import trocar_texto_do_link

PAGINA = (
    Path(__file__).parent
    / "fixtures"
    / "pagina_ru"
    / "cardapio-refeitorio-2026-11-21.html"
)
CAMPI_JSON = Path(__file__).parents[1] / "fixtures" / "campi.json"
UPLOADS = "https://ru.unb.br/wp-content/uploads/2026/11/"
# Texto dos links como está no HTML (o travessão vem como entidade).
LINK_16 = "ISM &#8211; 16/11/2026 À 22/11/2026"
LINK_23 = "ISM &#8211; 23/11/2026 À 29/11/2026"

SEMANA_16 = (date(2026, 11, 16), date(2026, 11, 22))
SEMANA_23 = (date(2026, 11, 23), date(2026, 11, 29))

# Os dois links de cada bloco da página de 21/11, conferidos no navegador.
ESPERADO = {
    "Darcy Ribeiro": [
        ("Darcy-Ribeiro-Semana-01-16-11-a-22-11-2.pdf", SEMANA_16),
        ("Darcy-Ribeiro-Semana-02-23-11-a-29-11.pdf", SEMANA_23),
    ],
    "Ceilândia": [
        # As datas do nome (16 a 21) não batem com as do link: vale o link.
        ("Ceilandia-Semana-01-16-11-a-21-11-1.pdf", SEMANA_16),
        ("Ceilandia-Semana-02-23-11-a-29-11-1.pdf", SEMANA_23),
    ],
    "Gama": [
        ("Gama-Semana-01-16-11-a-20-11-1.pdf", SEMANA_16),
        ("Gama-Semana-02-23-11-a-29-11.pdf", SEMANA_23),
    ],
    "Planaltina": [
        ("Planaltina-Semana-01-16-11-a-22-11-1.pdf", SEMANA_16),
        ("Planaltina-Semana-02-23-11-a-29-11.pdf", SEMANA_23),
    ],
    "Fazenda Água Limpa": [
        ("Fazenda-Semana-01-16-11-a-20-11-2.pdf", SEMANA_16),
        ("Fazenda-Agua-Limpa-Semana-02-23-11-a-29-11.pdf", SEMANA_23),
    ],
}


def _campi():
    """Os 5 campi da fixture, como objetos não salvos."""
    registros = json.loads(CAMPI_JSON.read_text(encoding="utf-8"))
    return {r["fields"]["nome"]: Campus(pk=r["pk"], **r["fields"]) for r in registros}


CAMPI = _campi()


def _html_real():
    return PAGINA.read_text(encoding="utf-8")


def _resposta(conteudo, status=200):
    resposta = mock.Mock(status_code=status)
    resposta.content = (
        conteudo.encode("utf-8") if isinstance(conteudo, str) else conteudo
    )
    return resposta


@pytest.fixture
def pagina():
    """Simula a página do RU; `pagina.html = ...` troca o HTML servido."""
    estado = mock.Mock(html=_html_real())
    with mock.patch(
        "apps.cardapio.leitor.cardapio_downloader.requests.get",
        side_effect=lambda url, **kwargs: _resposta(estado.html),
    ) as get:
        estado.get = get
        yield estado


def _localizar(nome):
    return CardapioDownloader().localizar_pdfs(CAMPI[nome])


def _resumo(fontes):
    return [(f.url, (f.inicio, f.fim), f.erro is None) for f in fontes]


def _esperado(nome):
    return [(UPLOADS + arquivo, semana, True) for arquivo, semana in ESPERADO[nome]]


# ------------------------------------------------------------ página real


@pytest.mark.parametrize("nome", list(ESPERADO))
def test_os_cinco_campi_acham_os_dois_links_certos(pagina, nome):
    fontes = _localizar(nome)
    assert _resumo(fontes) == _esperado(nome)
    assert all(f.campus is CAMPI[nome] for f in fontes)
    assert fontes[0].texto_link == "ISM – 16/11/2026 À 22/11/2026"


def test_le_a_url_da_pagina_do_settings_com_user_agent_e_tempo_limite(pagina, settings):
    settings.URL_PAGINA_CARDAPIO = "https://ru.unb.br/outra-pagina/"
    _localizar("Gama")
    pagina.get.assert_called_once()
    (url,), kwargs = pagina.get.call_args
    assert url == "https://ru.unb.br/outra-pagina/"
    assert "BandejaoUnB" in kwargs["headers"]["User-Agent"]
    assert 0 < kwargs["timeout"] <= 30
    assert kwargs["allow_redirects"] is False


def _secoes_por_bloco(soup):
    """As seções do Elementor agrupadas por bloco "Cardápio <campus>".

    Cada bloco começa na seção do título h3 e vai até a seção antes do
    próximo título de campus. O que vem antes e depois fica de fora.
    """
    raiz = soup.find("div", class_="elementor-12853")
    secoes = raiz.find_all("section", recursive=False)
    blocos, atual = [], None
    for secao in secoes:
        titulo = secao.find("h3")
        if titulo and titulo.get_text(strip=True).startswith("Cardápio"):
            atual = [secao]
            blocos.append(atual)
        elif atual is not None and secao.find("a", href=True):
            atual.append(secao)
        else:
            atual = None
    return blocos


def _blocos_em_outra_ordem(html):
    soup = BeautifulSoup(html, "html.parser")
    blocos = _secoes_por_bloco(soup)
    assert len(blocos) == 5
    marcador = blocos[0][0]
    ancora = soup.new_tag("div")
    marcador.insert_before(ancora)
    for bloco in blocos:
        for secao in bloco:
            secao.extract()
    # Fazenda, Planaltina, Gama, Ceilândia, Darcy: ao contrário.
    for bloco in reversed(blocos):
        for secao in bloco:
            ancora.insert_before(secao)
    ancora.decompose()
    return str(soup)


def test_blocos_em_outra_ordem_dao_o_mesmo_resultado(pagina):
    # Sabotagem do QA-10: "associar o link pela posição do bloco".
    pagina.html = _blocos_em_outra_ordem(_html_real())
    titulos = [
        h.get_text(strip=True)
        for h in BeautifulSoup(pagina.html, "html.parser").find_all("h3")
    ][:5]
    assert titulos[0] == "Cardápio Fazenda Água Limpa"
    assert titulos[-1] == "Cardápio Darcy Ribeiro"
    for nome in ESPERADO:
        assert _resumo(_localizar(nome)) == _esperado(nome)


def test_menu_com_o_mesmo_texto_do_titulo_nao_conta_como_titulo(pagina):
    # O menu tem "Cardápio Darcy Ribeiro" duas vezes, em <a>: só h1-h6 contam.
    menu = [
        a
        for a in BeautifulSoup(pagina.html, "html.parser").find_all("a")
        if a.get_text(strip=True) == "Cardápio Darcy Ribeiro"
    ]
    assert len(menu) == 2
    assert _resumo(_localizar("Darcy Ribeiro")) == _esperado("Darcy Ribeiro")


def test_pdf_de_outro_site_depois_do_ultimo_bloco_nao_entra(pagina):
    urls = [f.url for f in _localizar("Fazenda Água Limpa")]
    assert all(u.startswith("https://ru.unb.br/wp-content/uploads/") for u in urls)
    assert len(urls) == 2


# ------------------------------------------------------- variações do HTML


def _trocar(html, antigo, novo, vezes=1):
    assert html.count(antigo) >= vezes
    return html.replace(antigo, novo, vezes)


def _titulo(rotulo):
    return f'<h3 class="elementor-heading-title elementor-size-default">Cardápio {rotulo}</h3>'


def test_titulo_ausente_e_falha_do_campus_inteiro(pagina):
    pagina.html = _trocar(pagina.html, "Cardápio Gama</h3>", "Cardápio Gamma</h3>")
    with pytest.raises(FonteNaoEncontradaError, match="Cardápio Gama.*ausente"):
        _localizar("Gama")
    # Os outros campi continuam achando os links.
    assert _resumo(_localizar("Planaltina")) == _esperado("Planaltina")


def test_titulo_repetido_e_falha_do_campus_inteiro(pagina):
    soup = BeautifulSoup(pagina.html, "html.parser")
    rodape = next(h for h in soup.find_all("h3") if "Ouvidoria" in h.get_text())
    rodape.insert_before(BeautifulSoup(_titulo("Gama"), "html.parser"))
    pagina.html = str(soup)
    with pytest.raises(FonteNaoEncontradaError, match="repetido"):
        _localizar("Gama")


def test_titulo_com_acento_maiusculas_e_espacos_diferentes_e_aceito(pagina):
    pagina.html = _trocar(
        pagina.html, "Cardápio Ceilândia</h3>", "  CARDAPIO   ceilandia </h3>"
    )
    assert _resumo(_localizar("Ceilândia")) == _esperado("Ceilândia")


def test_titulo_que_nao_e_de_nenhum_campus_e_ignorado(pagina):
    # "Cardápio refeitório" (h1) já está na página real; um título novo, de
    # outro restaurante, encerra o bloco anterior e não vira campus.
    soup = BeautifulSoup(pagina.html, "html.parser")
    fazenda = soup.find("a", href=lambda h: h and "Fazenda-Agua-Limpa" in h)
    fazenda.insert_before(BeautifulSoup(_titulo("Executivo"), "html.parser"))
    pagina.html = str(soup)
    fontes = _localizar("Fazenda Água Limpa")
    assert _resumo(fontes) == _esperado("Fazenda Água Limpa")[:1]


def test_arquivo_de_outro_campus_no_bloco_reprova_so_aquele_link(pagina):
    pagina.html = _trocar(
        pagina.html,
        "Gama-Semana-02-23-11-a-29-11.pdf",
        "Planaltina-Semana-02-23-11-a-29-11.pdf",
    )
    fontes = _localizar("Gama")
    assert [f.erro is None for f in fontes] == [True, False]
    assert isinstance(fontes[1].erro, FonteNaoEncontradaError)
    assert "Planaltina-Semana-02" in str(fontes[1].erro)
    # A semana do link reprovado continua conhecida (para o "não publicado").
    assert (fontes[1].inicio, fontes[1].fim) == SEMANA_23


@pytest.mark.parametrize(
    "arquivo",
    [
        "Gama-Semana-02-23-11-a-29-11-1.pdf",
        "gama-semana-02.pdf",
        "GAMA-Semana-02.PDF",
    ],
)
def test_sufixo_e_maiusculas_no_nome_do_arquivo_sao_aceitos(pagina, arquivo):
    pagina.html = _trocar(pagina.html, "Gama-Semana-02-23-11-a-29-11.pdf", arquivo)
    assert _localizar("Gama")[1].erro is None


def test_nome_com_acento_e_aceito(pagina):
    pagina.html = _trocar(
        pagina.html,
        "Ceilandia-Semana-02-23-11-a-29-11-1.pdf",
        "Ceil%C3%A2ndia-Semana-02-23-11-a-29-11-1.pdf",
    )
    assert _localizar("Ceilândia")[1].erro is None


def test_prefixo_seguido_de_outra_coisa_que_nao_hifen_e_reprovado(pagina):
    pagina.html = _trocar(
        pagina.html,
        "Gama-Semana-02-23-11-a-29-11.pdf",
        "Gamaxyz-Semana-02-23-11-a-29-11.pdf",
    )
    assert isinstance(_localizar("Gama")[1].erro, FonteNaoEncontradaError)


def test_os_dois_arquivos_da_fazenda_comecam_pelo_prefixo(pagina):
    # "Fazenda-Semana-01-..." e "Fazenda-Agua-Limpa-Semana-02-...".
    assert [f.erro for f in _localizar("Fazenda Água Limpa")] == [None, None]


def test_dois_links_para_a_mesma_semana_reprovam_so_aquela_semana(pagina):
    pagina.html = trocar_texto_do_link(pagina.html, "Darcy-Ribeiro-Semana-02", LINK_16)
    # Agora o Darcy tem dois links da semana de 16/11.
    fontes = _localizar("Darcy Ribeiro")
    assert [(f.inicio, f.erro is None) for f in fontes] == [
        (SEMANA_16[0], False),
        (SEMANA_16[0], False),
    ]
    assert "mesma semana" in str(fontes[0].erro)
    # E a outra semana dos outros campi segue normal.
    assert _resumo(_localizar("Ceilândia")) == _esperado("Ceilândia")


def test_dois_links_para_a_mesma_semana_com_a_outra_semana_valida(pagina):
    soup = BeautifulSoup(pagina.html, "html.parser")
    link = soup.find("a", href=lambda h: h and "Gama-Semana-01" in h)
    copia = BeautifulSoup(str(link).replace("-1.pdf", "-2.pdf"), "html.parser")
    link.insert_after(copia)
    pagina.html = str(soup)
    fontes = _localizar("Gama")
    assert [(f.inicio, f.erro is None) for f in fontes] == [
        (SEMANA_16[0], False),
        (SEMANA_16[0], False),
        (SEMANA_23[0], True),
    ]


def test_link_com_mais_de_sete_dias_e_reprovado(pagina):
    # Revisão #218, item 9: um intervalo errado ("16/11 a 29/11") faria o P1
    # apagar refeições da semana seguinte, lida por outro link.
    pagina.html = trocar_texto_do_link(
        pagina.html, "Gama-Semana-01", "ISM &#8211; 16/11/2026 À 29/11/2026"
    )
    fontes = _localizar("Gama")
    assert isinstance(fontes[0].erro, FonteNaoEncontradaError)
    assert "mais de 7 dias" in str(fontes[0].erro)
    # A semana dele continua conhecida (para o "não publicado").
    assert (fontes[0].inicio, fontes[0].fim) == (SEMANA_16[0], SEMANA_23[1])


def test_links_sobrepostos_reprovam_os_dois(pagina):
    pagina.html = trocar_texto_do_link(
        pagina.html, "Gama-Semana-02", "ISM &#8211; 20/11/2026 À 26/11/2026"
    )
    fontes = _localizar("Gama")
    assert [f.erro is None for f in fontes] == [False, False]
    assert all("sobreposto" in str(f.erro) for f in fontes)
    # Os outros campi não são afetados.
    assert _resumo(_localizar("Planaltina")) == _esperado("Planaltina")


def test_links_que_dividem_um_dia_so_tambem_sao_sobrepostos(pagina):
    # 16 a 22/11 e 22 a 28/11: o domingo 22 estaria nas duas semanas.
    pagina.html = trocar_texto_do_link(
        pagina.html, "Gama-Semana-02", "ISM &#8211; 22/11/2026 À 28/11/2026"
    )
    assert all("sobreposto" in str(f.erro) for f in _localizar("Gama"))


def test_link_de_sete_dias_exatos_e_aceito(pagina):
    assert [f.erro for f in _localizar("Gama")] == [None, None]


@pytest.mark.parametrize(
    "texto",
    [
        "ISM - 23/11/2026 a 29/11/2026",
        "ISM — 23/11/2026 até 29/11/2026",
        "ISM – 23/11/2026 à 29/11/2026",
        "23/11/2026 À 29/11/2026",
    ],
)
def test_variacoes_do_texto_do_link_sao_lidas(pagina, texto):
    pagina.html = trocar_texto_do_link(pagina.html, "Gama-Semana-02", texto)
    fonte = _localizar("Gama")[1]
    assert (fonte.inicio, fonte.fim, fonte.erro) == (*SEMANA_23, None)


@pytest.mark.parametrize(
    "texto",
    [
        "ISM – Semana 2",
        "ISM – 23/11/2026",
        "ISM – 29/11/2026 À 23/11/2026",
        "ISM – 31/11/2026 À 06/12/2026",
    ],
)
def test_link_sem_datas_legiveis_e_reprovado(pagina, texto):
    pagina.html = trocar_texto_do_link(pagina.html, "Gama-Semana-02", texto)
    fonte = _localizar("Gama")[1]
    assert isinstance(fonte.erro, FonteNaoEncontradaError)
    assert fonte.inicio is None and fonte.fim is None
    assert "datas" in str(fonte.erro)


def test_link_relativo_e_resolvido_pela_url_da_pagina(pagina):
    pagina.html = _trocar(
        pagina.html,
        "https://ru.unb.br/wp-content/uploads/2026/11/Gama-Semana-02",
        "/wp-content/uploads/2026/11/Gama-Semana-02",
    )
    assert _resumo(_localizar("Gama")) == _esperado("Gama")


@pytest.mark.parametrize(
    "url",
    [
        "https://unity.unb.br/wp-content/uploads/2026/11/Gama-Semana-02.pdf",
        "https://ru.unb.br.exemplo.com/wp-content/uploads/2026/11/Gama-Semana-02.pdf",
        "https://ru.unb.br/outra-pasta/Gama-Semana-02.pdf",
        "http://ru.unb.br/wp-content/uploads/2026/11/Gama-Semana-02.pdf",
        "https://ru.unb.br/wp-content/uploads/2026/11/Gama-Semana-02.docx",
    ],
)
def test_link_fora_do_host_ou_da_pasta_de_uploads_nao_entra(pagina, url):
    pagina.html = _trocar(
        pagina.html, UPLOADS + "Gama-Semana-02-23-11-a-29-11.pdf", url
    )
    assert _resumo(_localizar("Gama")) == _esperado("Gama")[:1]


def test_bloco_sem_nenhum_link_devolve_lista_vazia(pagina):
    soup = BeautifulSoup(pagina.html, "html.parser")
    for link in soup.find_all("a", href=lambda h: h and "/Planaltina-" in h):
        link.decompose()
    pagina.html = str(soup)
    assert _localizar("Planaltina") == []


def test_fonte_pdf_guarda_os_dados_do_c4():
    campus = CAMPI["Gama"]
    fonte = FontePDF(campus, "u", "t", date(2026, 11, 23), date(2026, 11, 29))
    assert (fonte.campus, fonte.url, fonte.texto_link, fonte.erro) == (
        campus,
        "u",
        "t",
        None,
    )


# -------------------------------------------------------- página fora do ar


@pytest.mark.parametrize(
    "falha",
    [
        requests.ConnectionError("sem rede"),
        requests.Timeout("demorou"),
        requests.TooManyRedirects("laço"),
    ],
)
def test_pagina_fora_do_ar_e_download_error(falha):
    with (
        mock.patch(
            "apps.cardapio.leitor.cardapio_downloader.requests.get", side_effect=falha
        ) as get,
        pytest.raises(DownloadError, match="página do RU"),
    ):
        _localizar("Gama")
    # Nenhuma repetição em sequência curta: quem tenta de novo é o cron.
    assert get.call_count == 1


@pytest.mark.parametrize("status", [301, 404, 500, 503])
def test_pagina_com_http_diferente_de_200_e_download_error(status):
    with (
        mock.patch(
            "apps.cardapio.leitor.cardapio_downloader.requests.get",
            return_value=_resposta("<h3>Cardápio Gama</h3>", status),
        ),
        pytest.raises(DownloadError, match=f"HTTP {status}"),
    ):
        _localizar("Gama")


def test_a_pagina_e_lida_uma_vez_por_downloader(pagina):
    # ADR 0014: uma requisição à página por execução, não uma por campus.
    downloader = CardapioDownloader()
    for nome in ESPERADO:
        assert _resumo(downloader.localizar_pdfs(CAMPI[nome])) == _esperado(nome)
    assert pagina.get.call_count == 1


def test_pagina_fora_do_ar_nao_e_pedida_de_novo_na_mesma_execucao():
    downloader = CardapioDownloader()
    with mock.patch(
        "apps.cardapio.leitor.cardapio_downloader.requests.get",
        side_effect=requests.ConnectionError("sem rede"),
    ) as get:
        for nome in ("Gama", "Planaltina"):
            with pytest.raises(DownloadError, match="página do RU"):
                downloader.localizar_pdfs(CAMPI[nome])
    assert get.call_count == 1


# ------------------------------------------------------------------ baixar

PDF_GAMA = (
    Path(__file__).parent
    / "fixtures"
    / "cardapios"
    / "Gama-Semana-02-23-11-a-29-11.pdf"
)


def _fonte():
    return FontePDF(
        CAMPI["Gama"],
        UPLOADS + "Gama-Semana-02-23-11-a-29-11.pdf",
        "ISM – 23/11/2026 À 29/11/2026",
        *SEMANA_23,
    )


def test_baixar_devolve_o_conteudo_e_o_sha256():
    conteudo = PDF_GAMA.read_bytes()
    with mock.patch(
        "apps.cardapio.leitor.cardapio_downloader.requests.get",
        return_value=_resposta(conteudo),
    ) as get:
        arquivo = CardapioDownloader().baixar(_fonte())
    assert arquivo.conteudo == conteudo
    assert arquivo.sha256 == hashlib.sha256(conteudo).hexdigest()
    assert len(arquivo.sha256) == 64
    (url,), kwargs = get.call_args
    assert url == UPLOADS + "Gama-Semana-02-23-11-a-29-11.pdf"
    assert "BandejaoUnB" in kwargs["headers"]["User-Agent"]
    assert 0 < kwargs["timeout"] <= 30
    assert kwargs["allow_redirects"] is False


@pytest.mark.parametrize("status", [302, 403, 404, 500])
def test_baixar_com_http_diferente_de_200_e_download_error(status):
    with (
        mock.patch(
            "apps.cardapio.leitor.cardapio_downloader.requests.get",
            return_value=_resposta(b"%PDF-1.7", status),
        ),
        pytest.raises(DownloadError, match=f"HTTP {status}.*Gama-Semana-02"),
    ):
        CardapioDownloader().baixar(_fonte())


def test_baixar_com_tempo_esgotado_e_download_error():
    with (
        mock.patch(
            "apps.cardapio.leitor.cardapio_downloader.requests.get",
            side_effect=requests.Timeout("demorou"),
        ) as get,
        pytest.raises(DownloadError, match="Timeout"),
    ):
        CardapioDownloader().baixar(_fonte())
    assert get.call_count == 1


def test_resposta_que_nao_e_pdf_e_formato_invalido():
    # Página de erro do WordPress com status 200.
    with (
        mock.patch(
            "apps.cardapio.leitor.cardapio_downloader.requests.get",
            return_value=_resposta("<html><body>Página não encontrada</body></html>"),
        ),
        pytest.raises(FormatoPDFInvalidoError, match="não é um PDF"),
    ):
        CardapioDownloader().baixar(_fonte())


def test_fonte_pdf_sem_erro_exige_as_datas_e_nao_muda_depois():
    campus = CAMPI["Gama"]
    with pytest.raises(ValueError, match="datas"):
        FontePDF(campus, "u", "t", None, None)
    reprovada = FontePDF(campus, "u", "t", None, None, FonteNaoEncontradaError("x"))
    with pytest.raises(AttributeError):
        reprovada.erro = None


def test_sha256_sai_do_conteudo():
    assert ArquivoPDF(b"%PDF-1.7").sha256 == hashlib.sha256(b"%PDF-1.7").hexdigest()


# ------------------------------------------------------ FonteCardapioConfig


def test_config_le_rotulo_e_prefixo_do_campus_e_url_do_settings(settings):
    settings.URL_PAGINA_CARDAPIO = "https://ru.unb.br/teste/"
    config = FonteCardapioConfig()
    assert config.url_pagina == "https://ru.unb.br/teste/"
    fazenda = CAMPI["Fazenda Água Limpa"]
    assert config.rotulo(fazenda) == "Fazenda Água Limpa"
    assert config.prefixo_arquivo(fazenda) == "Fazenda"
