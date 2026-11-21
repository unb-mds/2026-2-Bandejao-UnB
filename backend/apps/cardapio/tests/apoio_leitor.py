"""Apoio dos testes do Leitor de Cardápio (BE-12, #139).

`SiteDoRUFalso` substitui o `requests.get` do `CardapioDownloader`: serve o
HTML real da página do RU (21/11/2026) e os PDFs reais das fixtures, pela
URL. Nenhuma requisição sai de verdade. Cada teste pode trocar o HTML, o
conteúdo de uma URL, ou fazer uma URL falhar.
"""

from pathlib import Path
from unittest import mock

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
