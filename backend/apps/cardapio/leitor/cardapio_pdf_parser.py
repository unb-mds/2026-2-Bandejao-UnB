"""Leitura do PDF semanal do cardápio (RF06, ADR 0003, Leitor N4).

Primeira versão, feita no BE-04 como teste com os PDFs reais do Gama, da
Ceilândia e do Darcy Ribeiro. Extrai de cada página a refeição, os dias, as
categorias, os pratos, a dieta e os marcadores de cada prato. Download,
gravação no banco e alertas ficam para o BE-12.

Biblioteca: pdfplumber (MIT). Ela entrega, com coordenadas, as palavras, as
bordas da tabela (retângulos finos) e as imagens dos ícones, com o conteúdo
de cada imagem. O Pillow (dependência do pdfplumber) compara os ícones.

Uso, para conferir um PDF à mão (dentro de backend/):
    python -m apps.cardapio.leitor.cardapio_pdf_parser cardapio.pdf [--json]
"""

import io
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field

import pdfplumber
from PIL import Image

MARCADORES_CONHECIDOS = {
    "cogumelo",
    "leite e derivados",
    "mel",
    "pimenta",
    "soja",
    "trigo/gluten",
    "amendoim",
    "oleaginosa",
    "ovo",
    "suino",
}

# Bordas da tabela: retângulos com no máximo esta espessura (pt).
ESPESSURA_MAX_BORDA = 2.5
# Ícone de marcador: imagem baixa dentro da tabela (pt). A largura não
# limita, porque o Word às vezes junta 2 ou 3 ícones numa imagem só.
ALTURA_MAX_ICONE = 25
# Distância média por pixel (0–255) acima da qual o ícone é "desconhecido".
# Nos PDFs testados (Gama, Ceilândia e Darcy), o pior acerto ficou em 28 e o
# erro mais próximo de um acerto ficou sempre 1,48 vez mais longe que ele.
DISTANCIA_MAX_ICONE = 35
# Abaixo desta razão (2ª distância / 1ª), o ícone é ambíguo e gera aviso.
RAZAO_MIN_ICONE = 1.3
LADO_ASSINATURA = 24

# Valores de TipoRefeicao e Dieta em apps/cardapio/models.py.
REFEICOES = {"cafedamanha": "cafe", "almoco": "almoco", "jantar": "jantar"}

RE_DATA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


class FormatoPDFInvalidoError(Exception):
    """O PDF não tem a tabela esperada: mantém o último cardápio válido."""


class LegendaInvalidaError(Exception):
    """Legenda diferente dos 10 marcadores: publica só em texto."""


class AssociacaoFalhouError(Exception):
    """Ícone desconhecido ou sem prato: publica só em texto."""


@dataclass
class PratoEstruturado:
    descricao: str
    marcadores: list = field(default_factory=list)


@dataclass
class CategoriaEstruturada:
    nome: str
    dieta: str | None
    pratos_por_dia: dict  # data ISO -> list[PratoEstruturado]


@dataclass
class RefeicaoEstruturada:
    refeicao: str
    dias: list  # [{"dia": "2ª FEIRA", "data": "2026-09-21"}]
    categorias: list


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


# ---------------------------------------------------------------- geometria


def _agrupar(valores, tolerancia=1.5):
    """Agrupa coordenadas próximas (bordas duplas) e devolve a média de cada grupo."""
    grupos = []
    for v in sorted(valores):
        if grupos and v - grupos[-1][-1] <= tolerancia:
            grupos[-1].append(v)
        else:
            grupos.append([v])
    return [sum(g) / len(g) for g in grupos]


def _centro(obj):
    return ((obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2)


class Grade:
    """Células da tabela, já com as células mescladas unidas.

    Monta a grade com todas as linhas horizontais e verticais e une duas
    células vizinhas quando não há borda desenhada entre elas.
    """

    def __init__(self, pagina):
        horiz = [
            r
            for r in pagina.rects
            if r["height"] <= ESPESSURA_MAX_BORDA and r["width"] > 20
        ]
        vert = [
            r
            for r in pagina.rects
            if r["width"] <= ESPESSURA_MAX_BORDA and r["height"] > 5
        ]
        if not horiz or not vert:
            raise FormatoPDFInvalidoError("tabela sem bordas")
        self.horiz, self.vert = horiz, vert
        self.ys = _agrupar([(r["top"] + r["bottom"]) / 2 for r in horiz])
        self.xs = _agrupar([(r["x0"] + r["x1"]) / 2 for r in vert])
        self.bbox = (self.xs[0], self.ys[0], self.xs[-1], self.ys[-1])
        self._unir_celulas()

    def _tem_borda_h(self, y, x0, x1):
        xm = (x0 + x1) / 2
        return any(
            abs((r["top"] + r["bottom"]) / 2 - y) <= 1.5 and r["x0"] <= xm <= r["x1"]
            for r in self.horiz
        )

    def _tem_borda_v(self, x, y0, y1):
        ym = (y0 + y1) / 2
        return any(
            abs((r["x0"] + r["x1"]) / 2 - x) <= 1.5 and r["top"] <= ym <= r["bottom"]
            for r in self.vert
        )

    def _unir_celulas(self):
        nl, nc = len(self.ys) - 1, len(self.xs) - 1
        pai = {(i, j): (i, j) for i in range(nl) for j in range(nc)}

        def raiz(a):
            while pai[a] != a:
                pai[a] = pai[pai[a]]
                a = pai[a]
            return a

        for i in range(nl):
            for j in range(nc):
                y0, y1 = self.ys[i], self.ys[i + 1]
                x0, x1 = self.xs[j], self.xs[j + 1]
                if j + 1 < nc and not self._tem_borda_v(self.xs[j + 1], y0, y1):
                    pai[raiz((i, j + 1))] = raiz((i, j))
                if i + 1 < nl and not self._tem_borda_h(self.ys[i + 1], x0, x1):
                    pai[raiz((i + 1, j))] = raiz((i, j))

        celulas = {}
        for i, j in pai:
            celulas.setdefault(raiz((i, j)), []).append((i, j))
        self.celulas = []
        for partes in celulas.values():
            i0 = min(i for i, _ in partes)
            i1 = max(i for i, _ in partes)
            j0 = min(j for _, j in partes)
            j1 = max(j for _, j in partes)
            self.celulas.append(
                {
                    "linhas": (i0, i1),
                    "colunas": (j0, j1),
                    "x0": self.xs[j0],
                    "x1": self.xs[j1 + 1],
                    "top": self.ys[i0],
                    "bottom": self.ys[i1 + 1],
                }
            )


# ------------------------------------------------------------------ ícones


def _imagem_pil(imagem_pdf):
    """Decodifica a imagem do PDF: JPEG (DCTDecode) ou RGB cru (FlateDecode)."""
    stream = imagem_pdf["stream"]
    filtros = stream.attrs.get("Filter")
    filtros = filtros if isinstance(filtros, list) else [filtros]
    if any(getattr(f, "name", f) == "DCTDecode" for f in filtros):
        return Image.open(io.BytesIO(stream.get_rawdata())).convert("RGB")
    w, h = imagem_pdf["srcsize"]
    dados = stream.get_data()
    if imagem_pdf.get("bits") != 8 or len(dados) < w * h * 3:
        return None
    return Image.frombytes("RGB", (w, h), dados[: w * h * 3])


def _recortar_tinta(img, limite=100):
    """Corta as bordas brancas, para o anel do ícone ocupar a imagem toda."""
    mascara = img.point(lambda v: 255 if v < 255 - limite / 3 else 0).convert("L")
    caixa = mascara.getbbox()
    return img.crop(caixa) if caixa else img


def _assinatura(img):
    """Conteúdo do ícone, sem bordas brancas, reduzido a LADO_ASSINATURA² px."""
    if img is None:
        return None
    return _recortar_tinta(img).resize(
        (LADO_ASSINATURA, LADO_ASSINATURA), Image.Resampling.LANCZOS
    )


def _faixas_com_tinta(img, limite=100, folga=1):
    """Faixas de colunas [início, fim) com algum pixel não branco.

    "Não branco" é a soma de quanto falta a R, G e B para 255 passar do
    limite: assim o anel amarelo do ovo e o rosa do suíno contam como tinta.
    """
    w, h = img.size
    px = img.load()
    tinta = [any(765 - sum(px[x, y]) > limite for y in range(h)) for x in range(w)]
    faixas, inicio, vazias = [], None, 0
    for x, t in enumerate(tinta + [False] * (folga + 1)):
        if t:
            if inicio is None:
                inicio = x
            vazias = 0
        elif inicio is not None:
            vazias += 1
            if vazias > folga:
                faixas.append((inicio, x - vazias + 1))
                inicio, vazias = None, 0
    # Descarta ruído (faixas muito estreitas para serem um ícone).
    faixas = [(i, f) for i, f in faixas if f - i >= h * 0.3]
    # Ícones encostados (anéis se tocando) ficam numa faixa só, bem mais
    # larga que alta: divide pela proporção.
    divididas = []
    for i, f in faixas:
        n = max(1, round((f - i) / h))
        divididas.extend(
            (i + k * (f - i) // n, i + (k + 1) * (f - i) // n) for k in range(n)
        )
    return divididas


def _distancia(a, b):
    pa, pb = a.tobytes(), b.tobytes()
    return sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)


class LegendaValidator:
    """Lê a legenda abaixo da tabela e confere os 10 marcadores conhecidos."""

    def extrair(self, pagina, grade):
        palavras = pagina.extract_words(x_tolerance=1.5)
        abaixo = [im for im in pagina.images if im["top"] > grade.bbox[3]]
        legenda = {}
        for im in abaixo:
            cx = (im["x0"] + im["x1"]) / 2
            rotulo = [
                p
                for p in palavras
                if 0 <= p["top"] - im["bottom"] <= 15
                and abs((p["x0"] + p["x1"]) / 2 - cx) <= 45
            ]
            # Palavras de rótulo vizinhos podem cair na janela: fica só o
            # grupo contíguo mais próximo do centro do ícone.
            rotulo.sort(key=lambda p: p["x0"])
            grupos = []
            for p in rotulo:
                if grupos and p["x0"] - grupos[-1][-1]["x1"] < 8:
                    grupos[-1].append(p)
                else:
                    grupos.append([p])
            if not grupos:
                continue
            grupo = min(
                grupos,
                key=lambda g: abs((g[0]["x0"] + g[-1]["x1"]) / 2 - cx),
            )
            nome = normalizar(" ".join(p["text"] for p in grupo))
            legenda[nome] = _assinatura(_imagem_pil(im))
        return legenda

    def validar(self, legenda):
        nomes = set(legenda)
        if nomes != MARCADORES_CONHECIDOS or any(v is None for v in legenda.values()):
            faltam = MARCADORES_CONHECIDOS - nomes
            sobram = nomes - MARCADORES_CONHECIDOS
            raise LegendaInvalidaError(
                f"faltam {sorted(faltam)}, sobram {sorted(sobram)}"
            )
        return True


# ----------------------------------------------------- pratos e associação


def _linhas_de_texto(palavras, tolerancia=3):
    linhas = []
    for p in sorted(palavras, key=lambda p: (p["top"], p["x0"])):
        if linhas and abs(p["top"] - linhas[-1][0]["top"]) <= tolerancia:
            linhas[-1].append(p)
        else:
            linhas.append([p])
    return [sorted(linha, key=lambda p: p["x0"]) for linha in linhas]


def _e_separador(texto):
    return texto.lower() == "ou"


# Palavras que deixam a frase em aberto no fim da linha: a linha seguinte
# continua o mesmo prato, mesmo começando com maiúscula ("Arroz branco e" /
# "Integral", no PDF da Ceilândia).
CONECTORES = {"e", "com", "de", "da", "do", "das", "dos", "ao", "à", "a", "em"}


def _linha_em_aberto(palavras):
    ultima = palavras[-1]["text"].lower()
    return ultima in CONECTORES or ultima.endswith((",", "-"))


class CardapioEstruturador:
    """Regras de negócio sobre o texto extraído (glossário, termo Prato)."""

    @staticmethod
    def separar_pratos(linhas):
        """Separa o texto de uma célula em pratos.

        - "ou"/"OU" separa pratos; "/" não separa (RF06.2).
        - Linha nova que começa com maiúscula começa outro prato
          ("Arroz branco e integral" / "Feijão preto"); com minúscula ou "(",
          continua o prato da linha anterior (quebra de linha do texto).
        - Exceção: se a linha anterior termina em conector ("e", "com", "de"...)
          ou vírgula, a linha nova continua o prato mesmo com maiúscula.

        Devolve a lista de pratos, cada um com as palavras que o formam.
        """
        pratos = []
        atual = []
        for linha in linhas:
            primeira = linha[0]["text"]
            if (
                atual
                and not _e_separador(primeira)
                and primeira[:1].isupper()
                and not _linha_em_aberto(atual)
            ):
                pratos.append(atual)
                atual = []
            for p in linha:
                if _e_separador(p["text"]):
                    if atual:
                        pratos.append(atual)
                    atual = []
                else:
                    atual.append(p)
        if atual:
            pratos.append(atual)
        return pratos


def _texto(palavras):
    texto = re.sub(r"\s+", " ", " ".join(p["text"] for p in palavras)).strip()
    # Palavra com hífen quebrada no fim da linha: "couve- flor" -> "couve-flor".
    return re.sub(r"(\w)- (\w)", r"\1-\2", texto)


class MarcadorIconMatcher:
    """Identifica cada ícone pela legenda e o associa a um prato pela posição.

    Os ícones são imagens fora da camada de texto do PDF (RF06.3).
    """

    @staticmethod
    def dividir(imagem_pdf):
        """Separa uma imagem com vários ícones lado a lado.

        O PDF do Word junta ícones vizinhos numa imagem só (104×52 = 2 ícones,
        156×52 = 3) e às vezes ainda achata a imagem (105×36 com 2 ícones
        ovais). Por isso a divisão é primeiro pelo conteúdo (colunas brancas
        entre os ícones) e depois pela proporção, quando os anéis se encostam.
        """
        img = _imagem_pil(imagem_pdf)
        x0, x1 = imagem_pdf["x0"], imagem_pdf["x1"]
        base = {"top": imagem_pdf["top"], "bottom": imagem_pdf["bottom"]}
        if img is None:
            return [{**base, "x0": x0, "x1": x1, "imagem": None}]
        w, h = img.size
        faixas = _faixas_com_tinta(img) or [(0, w)]
        escala = (x1 - x0) / w
        return [
            {
                **base,
                "x0": x0 + i * escala,
                "x1": x0 + f * escala,
                "imagem": img.crop((i, 0, f, h)),
            }
            for i, f in faixas
        ]

    @staticmethod
    def identificar(icone, legenda):
        """Marcador da legenda mais parecido e as duas menores distâncias."""
        assinatura = _assinatura(icone["imagem"])
        if assinatura is None:
            raise AssociacaoFalhouError("ícone em formato de imagem não suportado")
        distancias = sorted(
            (_distancia(assinatura, ref), nome) for nome, ref in legenda.items()
        )
        melhor, nome = distancias[0]
        if melhor > DISTANCIA_MAX_ICONE:
            raise AssociacaoFalhouError(f"ícone desconhecido (distância {melhor:.1f})")
        return nome, melhor, distancias[1][0]

    @staticmethod
    def associar(icone, pratos):
        """Índice do prato do ícone, decidido pela posição.

        1. Ícone na mesma linha de um texto: prato da última palavra à esquerda
           dele ("Pão francês [trigo] ou", "Leite [leite] OU Bebida de Soja [soja]").
        2. Ícone numa linha só de ícones: prato da linha de texto mais próxima
           acima dele ("Ovos mexidos" / "[leite][ovo]").
        """
        cx, cy = _centro(icone)
        mesma_linha = [
            (indice, p)
            for indice, prato in enumerate(pratos)
            for p in prato
            if p["top"] - 6 <= cy <= p["bottom"] + 6
        ]
        if mesma_linha:
            a_esquerda = [(i, p) for i, p in mesma_linha if p["x1"] <= icone["x0"] + 2]
            if a_esquerda:
                return max(a_esquerda, key=lambda ip: ip[1]["x1"])[0]
            return min(mesma_linha, key=lambda ip: abs(ip[1]["x0"] - cx))[0]
        acima = [
            (indice, p)
            for indice, prato in enumerate(pratos)
            for p in prato
            if p["bottom"] <= icone["top"] + 2
        ]
        if acima:
            return max(
                acima, key=lambda ip: (ip[1]["bottom"], -abs(_centro(ip[1])[0] - cx))
            )[0]
        raise AssociacaoFalhouError(
            f"ícone sem prato acima nem ao lado em ({cx:.0f}, {cy:.0f})"
        )


# ------------------------------------------------------------ página


DIETAS = {
    "padrao": "padrao",
    "ovolactovegetariano": "ovolacto",
    "vegetariano estrito": "vegetariano_estrito",
}


def _dieta(nome_categoria):
    nome = normalizar(nome_categoria)
    if not nome.startswith(("prato principal", "complemento")):
        return None
    for chave, dieta in DIETAS.items():
        if nome.endswith(chave):
            return dieta
    return None


def _nome_refeicao(pagina, coluna):
    # Texto girado 90°: os caracteres ficam empilhados e se leem de baixo para cima.
    chars = [
        c
        for c in pagina.chars
        if coluna["x0"] <= (c["x0"] + c["x1"]) / 2 <= coluna["x1"]
        and coluna["top"] <= (c["top"] + c["bottom"]) / 2 <= coluna["bottom"]
        and c["text"].strip()
    ]
    chars.sort(key=lambda c: -c["top"])
    # Os espaços somem no texto girado ("Cafédamanhã"): compara sem espaços.
    lido = "".join(c["text"] for c in chars)
    chave = normalizar(lido).replace(" ", "")
    if chave not in REFEICOES:
        raise FormatoPDFInvalidoError(f"refeição desconhecida: {lido!r}")
    return REFEICOES[chave]


class CardapioPDFParser:
    """Lê o PDF inteiro: uma RefeicaoEstruturada por página."""

    def __init__(self, caminho):
        self.caminho = caminho

    def extrair(self):
        resultados, problemas = [], []
        with pdfplumber.open(self.caminho) as pdf:
            for numero, pagina in enumerate(pdf.pages, start=1):
                refeicao, avisos = self._pagina(pagina)
                resultados.append(refeicao)
                problemas.extend(f"pág. {numero}: {a}" for a in avisos)
        return resultados, problemas

    def _pagina(self, pagina):
        avisos = []
        grade = Grade(pagina)

        def palavras_em(celula):
            # Palavras extraídas por célula: na página inteira, o pdfplumber
            # junta numa "linha" textos de alturas próximas em células
            # vizinhas e embaralha as letras de rótulos em fonte menor.
            def dentro(obj):
                cx, cy = _centro(obj)
                return (
                    celula["x0"] <= cx <= celula["x1"]
                    and celula["top"] <= cy <= celula["bottom"]
                )

            return pagina.filter(dentro).extract_words(x_tolerance=1.5)

        # Cabeçalho: célula "COMPOSIÇÃO" define a coluna das categorias; as
        # colunas à direita, na mesma faixa, são os dias.
        cabecalho = [c for c in grade.celulas if c["linhas"][0] == 0]
        col_categoria = next(
            (c for c in cabecalho if "COMPOSI" in _texto(palavras_em(c)).upper()),
            None,
        )
        if col_categoria is None:
            raise FormatoPDFInvalidoError("cabeçalho sem a coluna COMPOSIÇÃO")
        col_refeicao = min(cabecalho, key=lambda c: c["x0"])
        linhas_cabecalho = col_categoria["linhas"][1]
        dias = []
        for c in sorted(cabecalho, key=lambda c: c["x0"]):
            if c["x0"] < col_categoria["x1"] - 1:
                continue
            texto = _texto(palavras_em(c))
            data = next((m for m in map(RE_DATA.match, texto.split()) if m), None)
            if not data:
                continue
            d, m, a = (int(g) for g in data.groups())
            dias.append(
                {
                    "dia": texto.split(data.group(0))[0].strip(),
                    "data": f"{a:04d}-{m:02d}-{d:02d}",
                    "colunas": c["colunas"],
                }
            )

        # Legenda e assinaturas dos ícones.
        validador = LegendaValidator()
        legenda = validador.extrair(pagina, grade)
        validador.validar(legenda)

        # Categorias: células da coluna de categorias abaixo do cabeçalho.
        categorias = []
        celulas_cat = sorted(
            (
                c
                for c in grade.celulas
                if c["colunas"] == col_categoria["colunas"]
                and c["linhas"][0] > linhas_cabecalho
            ),
            key=lambda c: c["top"],
        )
        icones = [
            icone
            for im in pagina.images
            if im["bottom"] - im["top"] <= ALTURA_MAX_ICONE
            and grade.bbox[1] <= _centro(im)[1] <= grade.bbox[3]
            for icone in MarcadorIconMatcher.dividir(im)
        ]
        icones_usados = set()
        for cat in celulas_cat:
            nome = _texto(palavras_em(cat))
            pratos_por_dia = {d["data"]: [] for d in dias}
            dados = [
                c
                for c in grade.celulas
                if c["x0"] >= col_categoria["x1"] - 1
                and c["top"] >= cat["top"] - 1
                and c["bottom"] <= cat["bottom"] + 1
            ]
            for celula in sorted(dados, key=lambda c: (c["top"], c["x0"])):
                linhas = _linhas_de_texto(palavras_em(celula))
                grupos = CardapioEstruturador.separar_pratos(linhas)
                pratos = [PratoEstruturado(_texto(g)) for g in grupos]
                for im in icones:
                    cx, cy = _centro(im)
                    if not (
                        celula["x0"] <= cx <= celula["x1"]
                        and celula["top"] <= cy <= celula["bottom"]
                    ):
                        continue
                    icones_usados.add(id(im))
                    marcador, dist, segunda = MarcadorIconMatcher.identificar(
                        im, legenda
                    )
                    if segunda < dist * RAZAO_MIN_ICONE:
                        avisos.append(
                            f"{nome}: ícone {marcador} com pouca margem "
                            f"({dist:.1f} contra {segunda:.1f})"
                        )
                    indice = MarcadorIconMatcher.associar(im, grupos)
                    if marcador not in pratos[indice].marcadores:
                        pratos[indice].marcadores.append(marcador)
                # Célula mesclada vale para todos os dias que ela cobre.
                cobertos = [
                    d
                    for d in dias
                    if celula["colunas"][0] <= d["colunas"][0]
                    and d["colunas"][1] <= celula["colunas"][1]
                ]
                for d in cobertos:
                    pratos_por_dia[d["data"]].extend(
                        PratoEstruturado(p.descricao, list(p.marcadores))
                        for p in pratos
                    )
            categorias.append(CategoriaEstruturada(nome, _dieta(nome), pratos_por_dia))

        soltos = [im for im in icones if id(im) not in icones_usados]
        if soltos:
            raise AssociacaoFalhouError(
                f"{len(soltos)} ícone(s) fora das células de pratos"
            )

        refeicao = RefeicaoEstruturada(
            refeicao=_nome_refeicao(pagina, col_refeicao),
            dias=[{"dia": d["dia"], "data": d["data"]} for d in dias],
            categorias=categorias,
        )
        return refeicao, avisos


def imprimir(refeicao):
    print(f"\n=== {refeicao.refeicao} ===")
    for d in refeicao.dias:
        print(f"\n--- {d['dia']} {d['data']} ---")
        for cat in refeicao.categorias:
            pratos = cat.pratos_por_dia.get(d["data"], [])
            if not pratos:
                continue
            dieta = f" [{cat.dieta}]" if cat.dieta else ""
            print(f"  {cat.nome}{dieta}")
            for p in pratos:
                marc = f"  <{', '.join(p.marcadores)}>" if p.marcadores else ""
                print(f"    - {p.descricao}{marc}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    refeicoes, avisos = CardapioPDFParser(argv[1]).extrair()
    if "--json" in argv:
        print(json.dumps([asdict(r) for r in refeicoes], ensure_ascii=False, indent=2))
    else:
        for r in refeicoes:
            imprimir(r)
        for a in avisos:
            print("AVISO:", a)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
