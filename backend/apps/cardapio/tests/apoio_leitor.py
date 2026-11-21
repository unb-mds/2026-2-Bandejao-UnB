"""Apoio dos testes do Leitor de Cardápio (BE-12, #139).

`SiteDoRUFalso` substitui o `requests.get` do `CardapioDownloader`: serve o
HTML real da página do RU (21/11/2026) e os PDFs reais das fixtures, pela
URL. Nenhuma requisição sai de verdade. Cada teste pode trocar o HTML, o
conteúdo de uma URL, ou fazer uma URL falhar.
"""

import re
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from apps.cardapio.leitor.cardapio_pdf_parser import (
    AssociacaoFalhouError,
    CardapioPDFParser,
)

FIXTURES = Path(__file__).parent / "fixtures"
PAGINA = FIXTURES / "pagina_ru" / "cardapio-refeitorio-2026-11-21.html"
PDFS = FIXTURES / "cardapios"
UPLOADS = "https://ru.unb.br/wp-content/uploads/2026/11/"

URL_GAMA_16 = UPLOADS + "Gama-Semana-01-16-11-a-20-11-1.pdf"
URL_GAMA_23 = UPLOADS + "Gama-Semana-02-23-11-a-29-11.pdf"
URL_PLANALTINA_23 = UPLOADS + "Planaltina-Semana-02-23-11-a-29-11.pdf"
URL_FAZENDA_16 = UPLOADS + "Fazenda-Semana-01-16-11-a-20-11-2.pdf"

# Texto dos links como está no HTML (o travessão vem como entidade).
LINK_16 = "ISM &#8211; 16/11/2026 À 22/11/2026"
LINK_23 = "ISM &#8211; 23/11/2026 À 29/11/2026"


def trocar_texto_do_link(html, trecho_do_href, novo_texto):
    """Troca o texto de um único link, achado pelo href.

    Não depende da ordem dos blocos na página, que a ADR 0014 não garante.
    """
    padrao = re.compile(
        r'(<a [^>]*href="[^"]*'
        + re.escape(trecho_do_href)
        + r'[^"]*"[^>]*>)(.*?)(</a>)',
        re.DOTALL,
    )
    novo, quantos = padrao.subn(lambda m: m.group(1) + novo_texto + m.group(3), html)
    assert quantos == 1, f"{quantos} links com {trecho_do_href!r}"
    return novo


@contextmanager
def falhar_associacao_na_refeicao(refeicao):
    """Faz a associação dos ícones falhar nas páginas de uma refeição.

    A falha nasce onde nasceria de verdade (`AssociacaoFalhouError` na
    leitura com marcadores), e o parser segue o caminho real: relê a página
    só em texto. Não depende do número da página nem de coordenadas.
    """
    original = CardapioPDFParser._pagina

    def _pagina(self, pagina, com_marcadores=True):
        lida = original(self, pagina, com_marcadores)
        if com_marcadores and lida.refeicao == refeicao:
            raise AssociacaoFalhouError("ícone desconhecido (simulado no teste)")
        return lida

    with mock.patch.object(CardapioPDFParser, "_pagina", _pagina):
        yield


def pdf(nome):
    return (PDFS / nome).read_bytes()


class SiteDoRUFalso:
    """O site do RU numa caixa: página real e os PDFs que estão nas fixtures.

    URL sem conteúdo cadastrado responde 404, como um link quebrado.
    """

    def __init__(self):
        self.html = PAGINA.read_text(encoding="utf-8")
        self.conteudos = {
            URL_GAMA_16: pdf("Gama-Semana-01-16-11-a-20-11-1.pdf"),
            URL_GAMA_23: pdf("Gama-Semana-02-23-11-a-29-11.pdf"),
            URL_PLANALTINA_23: pdf("Planaltina-Semana-02-23-11-a-29-11.pdf"),
            URL_FAZENDA_16: pdf("Fazenda-Semana-01-16-11-a-20-11-2.pdf"),
        }
        self.pedidos = []

    def trocar_no_html(self, antigo, novo, vezes=1):
        assert self.html.count(antigo) >= vezes, antigo
        self.html = self.html.replace(antigo, novo, vezes)

    def trocar_texto_do_link(self, trecho_do_href, novo_texto):
        self.html = trocar_texto_do_link(self.html, trecho_do_href, novo_texto)

    def get(self, url, **kwargs):
        self.pedidos.append(url)
        if url.startswith("https://ru.unb.br/cardapio-refeitorio"):
            return self._resposta(self.html.encode("utf-8"))
        conteudo = self.conteudos.get(url)
        if isinstance(conteudo, Exception):
            raise conteudo
        if isinstance(conteudo, int):
            return self._resposta(b"", conteudo)
        if conteudo is None:
            return self._resposta(b"<html>404</html>", 404)
        return self._resposta(conteudo)

    @staticmethod
    def _resposta(conteudo, status=200):
        resposta = mock.Mock(status_code=status)
        resposta.content = conteudo
        return resposta

    def __enter__(self):
        self._patch = mock.patch(
            "apps.cardapio.leitor.cardapio_downloader.requests.get", self.get
        )
        self._patch.start()
        return self

    def __exit__(self, *erro):
        self._patch.stop()
