"""CardapioDownloader: acha e baixa o PDF de cada campus (Leitor N4 4c, ADR 0014).

Analogia: é o carteiro que procura a caixa de correio pelo nome escrito
nela, nunca pela posição na rua. Na página de cardápios do RU, cada campus
tem um bloco com o título "Cardápio <rótulo>" e, abaixo dele, um link por
semana. O campus vem do título; o nome do arquivo e as datas do link só
conferem. A ordem dos blocos na página nunca é usada.

Toda requisição leva o `User-Agent` do projeto e tempo limite, e não há
repetição em sequência curta: quem tenta de novo é o cron, 3 horas depois.
A página é lida uma vez por instância (uma por execução do comando), e não
uma por campus: se ela falha, os outros campi recebem a mesma falha.
"""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from apps.cardapio.leitor.cardapio_pdf_parser import (
    DownloadError,
    FonteNaoEncontradaError,
    FormatoPDFInvalidoError,
    normalizar,
)
from apps.cardapio.leitor.fonte_cardapio_config import FonteCardapioConfig
from apps.cardapio.models import Campus

USER_AGENT = "BandejaoUnB/1.0 (+https://bandejaounb.com.br)"
# Segundos de espera pela conexão e por cada leitura da resposta.
TEMPO_LIMITE = 30

HOST_DO_RU = "ru.unb.br"
PASTA_DE_UPLOADS = "/wp-content/uploads/"
TITULOS = ("h1", "h2", "h3", "h4", "h5", "h6")
PREFIXO_DO_TITULO = "cardapio "

# "ISM – 16/11/2026 À 22/11/2026", depois do `normalizar` (sem acento e em
# minúsculas): "ism – 16/11/2026 a 22/11/2026". Aceita "a", "ate", hífen,
# travessão e meia-risca entre as datas.
RE_DATAS_DO_LINK = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4})\s*(?:a|ate|-|–|—)\s*(\d{1,2})/(\d{1,2})/(\d{4})"
)


@dataclass
class FontePDF:
    """Um link de PDF do bloco do campus, uma semana.

    `inicio` e `fim` são as datas do texto do link; `None` se ele não tem
    datas legíveis. `erro` é a `FonteNaoEncontradaError` de um link
    reprovado (arquivo de outro campus, semana repetida, datas ilegíveis):
    o `LeitorCardapioService` alerta e não baixa esse link, mas a semana
    dele ainda conta para o alerta de "não publicado" (ADR 0014).
    """

    campus: Campus
    url: str
    texto_link: str
    inicio: date | None
    fim: date | None
    erro: FonteNaoEncontradaError | None = None


@dataclass(frozen=True)
class ArquivoPDF:
    conteudo: bytes
    sha256: str


def _datas_do_link(texto):
    """(início, fim) do texto do link, ou None se não há duas datas válidas
    em ordem."""
    m = RE_DATAS_DO_LINK.search(normalizar(texto))
    if not m:
        return None
    d1, m1, a1, d2, m2, a2 = (int(g) for g in m.groups())
    try:
        inicio, fim = date(a1, m1, d1), date(a2, m2, d2)
    except ValueError:
        return None
    return (inicio, fim) if inicio <= fim else None


def _e_pdf_do_ru(url):
    partes = urlsplit(url)
    return (
        partes.scheme == "https"
        and partes.hostname == HOST_DO_RU
        and partes.path.startswith(PASTA_DE_UPLOADS)
        and partes.path.lower().endswith(".pdf")
    )


class CardapioDownloader:
    def __init__(self, config: FonteCardapioConfig | None = None):
        self.config = config or FonteCardapioConfig()
        # Conteúdo da página ou o `DownloadError` da primeira tentativa.
        self._pagina: bytes | DownloadError | None = None

    # ------------------------------------------------------------ descoberta

    def localizar_pdfs(self, campus: Campus) -> list[FontePDF]:
        """Os links do bloco do campus, um por semana, na ordem da página.

        Lança `DownloadError` se a página não pôde ser lida e
        `FonteNaoEncontradaError` se o título do campus falta ou se repete:
        nesses casos o Leitor não escolhe nenhum link. Os problemas de um
        link só (arquivo de outro campus, semana repetida, datas ilegíveis)
        ficam no `erro` da `FontePDF` daquele link.
        """
        blocos = self._blocos_por_titulo(self._ler_pagina())
        rotulo = self.config.rotulo(campus)
        encontrados = blocos.get(normalizar(rotulo), [])
        if not encontrados:
            raise FonteNaoEncontradaError(
                f"título 'Cardápio {rotulo}' ausente na página do RU"
            )
        if len(encontrados) > 1:
            raise FonteNaoEncontradaError(
                f"título 'Cardápio {rotulo}' repetido na página do RU "
                f"({len(encontrados)} vezes)"
            )

        fontes = []
        for url, texto in encontrados[0]:
            datas = _datas_do_link(texto)
            fonte = FontePDF(campus, url, texto, *(datas or (None, None)))
            if datas is None:
                fonte.erro = FonteNaoEncontradaError(
                    f"link sem datas legíveis: {texto!r} ({url})"
                )
            elif not self._conferir_arquivo(campus, url):
                fonte.erro = FonteNaoEncontradaError(
                    f"o arquivo não começa por "
                    f"'{self.config.prefixo_arquivo(campus)}-': {url}"
                )
            fontes.append(fonte)

        # Dois links para a mesma semana: o Leitor não escolhe um deles.
        por_semana = Counter(f.inicio for f in fontes if f.inicio is not None)
        for fonte in fontes:
            if fonte.inicio is not None and por_semana[fonte.inicio] > 1:
                fonte.erro = FonteNaoEncontradaError(
                    f"{por_semana[fonte.inicio]} links para a mesma semana "
                    f"({fonte.inicio:%d/%m/%Y}): {fonte.url}"
                )
        return fontes

    def _ler_pagina(self) -> bytes:
        if self._pagina is None:
            try:
                self._pagina = self._get(self.config.url_pagina, "página do RU").content
            except DownloadError as exc:
                self._pagina = exc
        if isinstance(self._pagina, DownloadError):
            raise self._pagina
        return self._pagina

    def _blocos_por_titulo(self, html) -> dict[str, list[list[tuple[str, str]]]]:
        """Rótulo normalizado -> blocos com esse título; cada bloco é a lista
        de (url, texto) dos links de PDF entre o título e o próximo título.

        Só cabeçalhos (h1 a h6) contam como título: o menu da página também
        tem "Cardápio Darcy Ribeiro", em links. Qualquer cabeçalho encerra o
        bloco anterior; o que não é "Cardápio <rótulo>" não abre bloco.
        """
        sopa = BeautifulSoup(html, "html.parser")
        blocos: dict[str, list[list[tuple[str, str]]]] = {}
        atual = None
        for elemento in sopa.find_all((*TITULOS, "a")):
            if elemento.name in TITULOS:
                titulo = normalizar(elemento.get_text(" "))
                atual = None
                if titulo.startswith(PREFIXO_DO_TITULO):
                    rotulo = titulo.removeprefix(PREFIXO_DO_TITULO)
                    atual = []
                    blocos.setdefault(rotulo, []).append(atual)
            elif atual is not None and elemento.get("href"):
                url = urljoin(self.config.url_pagina, elemento["href"].strip())
                if _e_pdf_do_ru(url):
                    atual.append((url, " ".join(elemento.get_text(" ").split())))
        return blocos

    def _conferir_arquivo(self, campus: Campus, url: str) -> bool:
        """O nome do arquivo começa pelo prefixo do campus seguido de "-"
        (ou é só o prefixo), ignorando acentos e maiúsculas. Os sufixos
        "-1", "-2" do WordPress ficam no fim e não atrapalham."""
        nome = normalizar(PurePosixPath(unquote(urlsplit(url).path)).stem)
        prefixo = normalizar(self.config.prefixo_arquivo(campus))
        return nome == prefixo or nome.startswith(prefixo + "-")

    # -------------------------------------------------------------- download

    def baixar(self, fonte: FontePDF) -> ArquivoPDF:
        """Baixa o PDF do link. `DownloadError` em falha de rede, tempo
        esgotado ou HTTP diferente de 200; `FormatoPDFInvalidoError` se a
        resposta não é um PDF (ex.: uma página de erro com status 200)."""
        conteudo = self._get(fonte.url, "PDF").content
        if not conteudo.startswith(b"%PDF"):
            raise FormatoPDFInvalidoError(f"a resposta não é um PDF: {fonte.url}")
        return ArquivoPDF(conteudo, hashlib.sha256(conteudo).hexdigest())

    @staticmethod
    def _get(url, o_que):
        try:
            resposta = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TEMPO_LIMITE,
                # Um redirecionamento poderia levar a outro host; vira falha
                # visível (alerta), em vez de ser seguido.
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise DownloadError(
                f"falha ao baixar a {o_que} ({type(exc).__name__}): {url}"
            ) from exc
        if resposta.status_code != 200:
            raise DownloadError(
                f"HTTP {resposta.status_code} ao baixar a {o_que}: {url}"
            )
        return resposta
