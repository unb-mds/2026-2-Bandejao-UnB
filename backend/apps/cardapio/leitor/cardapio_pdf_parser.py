"""Leitura do PDF semanal do cardápio (RF06, ADR 0003, Leitor N4).

Primeira versão, feita no BE-04 como teste com os PDFs reais do Gama, da
Ceilândia e do Darcy Ribeiro. Extrai de cada página a refeição, os dias, as
categorias, os pratos, a dieta e os marcadores de cada prato. Download,
gravação no banco e alertas ficam para o BE-12.

Biblioteca: pdfplumber (MIT). Ela entrega, com coordenadas, as palavras, as
bordas da tabela (retângulos finos) e as imagens dos ícones, com o conteúdo
de cada imagem. O Pillow (dependência do pdfplumber) compara os ícones.

Quando algo foge do esperado, o leitor nunca devolve um cardápio vazio ou
incompleto em silêncio:
- `FormatoPDFInvalidoError`: o PDF inteiro é recusado (o BE-12 mantém o
  último cardápio válido, RF06.4);
- `LegendaInvalidaError` e `AssociacaoFalhouError`: só a página afetada sai
  sem marcadores, com `alergenos_indisponiveis=True` e o motivo (RF06.3).

Uso, para conferir um PDF à mão (dentro de backend/):
    python -m apps.cardapio.leitor.cardapio_pdf_parser cardapio.pdf [--json]
"""

import datetime
import io
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field

import pdfplumber
from pdfminer.psexceptions import PSException
from pdfplumber.utils.exceptions import PdfminerException
from PIL import Image

# Rótulo da legenda (normalizado) -> nome do MARCADOR no dicionário de dados
# (docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md).
ROTULOS_MARCADORES = {
    "cogumelo": "cogumelo",
    "leite e derivados": "leite_e_derivados",
    "mel": "mel",
    "pimenta": "pimenta",
    "soja": "soja",
    "trigo/gluten": "trigo_gluten",
    "amendoim": "amendoim",
    "oleaginosa": "oleaginosa",
    "ovo": "ovo",
    "suino": "suino",
}

# Bordas da tabela: retângulos com no máximo esta espessura (pt).
ESPESSURA_MAX_BORDA = 2.5
# Ícone de marcador: imagem baixa dentro da tabela (pt). A largura não
# limita, porque o Word às vezes junta 2 ou 3 ícones numa imagem só.
# Imagem mais alta que isso dentro da tabela é um erro (AssociacaoFalhouError).
ALTURA_MAX_ICONE = 25
# Distância média por pixel (0–255) acima da qual o ícone é "desconhecido".
# Nos PDFs testados (Gama, Ceilândia e Darcy), o pior acerto ficou em 28 e o
# segundo colocado ficou sempre pelo menos 1,48 vez mais longe que o certo.
DISTANCIA_MAX_ICONE = 35
# Abaixo desta razão (2ª distância / 1ª), o ícone é ambíguo e a associação
# falha: melhor sem marcadores do que com um marcador errado.
RAZAO_MIN_ICONE = 1.3
LADO_ASSINATURA = 24

# Valores de TipoRefeicao e Dieta em apps/cardapio/models.py.
REFEICOES = {"cafedamanha": "cafe", "almoco": "almoco", "jantar": "jantar"}
DIETAS = {
    "padrao": "padrao",
    "ovolactovegetariano": "ovolacto",
    "vegetariano estrito": "vegetariano_estrito",
}

ROTULO_COMPOSICAO = "COMPOSI"
# Dia da semana do cabeçalho (normalizado: "2ª FEIRA" vira "2a feira") ->
# datetime.date.weekday(), de 0 (segunda) a 6 (domingo).
DIAS_DA_SEMANA = {
    "2a feira": 0,
    "segunda-feira": 0,
    "segunda": 0,
    "3a feira": 1,
    "terca-feira": 1,
    "terca": 1,
    "4a feira": 2,
    "quarta-feira": 2,
    "quarta": 2,
    "5a feira": 3,
    "quinta-feira": 3,
    "quinta": 3,
    "6a feira": 4,
    "sexta-feira": 4,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}
RE_DATA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})$")


class LeitorCardapioError(Exception):
    """Base das falhas do leitor: um só `except` no BE-12."""


class FormatoPDFInvalidoError(LeitorCardapioError):
    """O arquivo não é o PDF esperado: mantém o último cardápio válido."""


class LegendaInvalidaError(LeitorCardapioError):
    """Legenda diferente dos 10 marcadores: a página sai só em texto."""


class AssociacaoFalhouError(LeitorCardapioError):
    """Ícone desconhecido, ambíguo ou sem prato: a página sai só em texto."""


@dataclass
class PratoEstruturado:
    descricao: str
    marcadores: list[str] = field(default_factory=list)


@dataclass
class CategoriaEstruturada:
    nome: str
    dieta: str | None
    pratos_por_dia: dict[str, list[PratoEstruturado]]  # chave: data ISO


@dataclass
class RefeicaoEstruturada:
    refeicao: str
    dias: list[dict[str, str]]  # [{"dia": "2ª FEIRA", "data": "2026-09-21"}]
    categorias: list[CategoriaEstruturada]
    alergenos_indisponiveis: bool = False
    motivo: str | None = None


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


def _dentro(obj, caixa):
    cx, cy = _centro(obj)
    return caixa["x0"] <= cx <= caixa["x1"] and caixa["top"] <= cy <= caixa["bottom"]


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
        self.caixa = {
            "x0": self.xs[0],
            "top": self.ys[0],
            "x1": self.xs[-1],
            "bottom": self.ys[-1],
        }
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


def _nomes(valor):
    valores = valor if isinstance(valor, list) else [valor]
    return [getattr(v, "name", v) for v in valores]


def _imagem_pil(imagem_pdf):
    """Decodifica a imagem do PDF, ou devolve None se o formato não for aceito.

    Aceita JPEG (DCTDecode, em qualquer espaço de cor) e RGB de 8 bits nos
    filtros que o pdfminer decodifica (FlateDecode nos PDFs testados).
    """
    stream = imagem_pdf["stream"]
    try:
        if "DCTDecode" in _nomes(stream.attrs.get("Filter")):
            return Image.open(io.BytesIO(stream.get_rawdata())).convert("RGB")
        if "DeviceRGB" not in _nomes(imagem_pdf.get("colorspace") or []):
            return None
        w, h = imagem_pdf["srcsize"]
        dados = stream.get_data()
        if imagem_pdf.get("bits") != 8 or len(dados) < w * h * 3:
            return None
        return Image.frombytes("RGB", (w, h), dados[: w * h * 3])
    except (OSError, ValueError, PSException):
        return None


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
        """Rótulo normalizado -> assinatura do ícone (None se não decodificou)."""
        palavras = pagina.extract_words(x_tolerance=1.5)
        abaixo = [im for im in pagina.images if im["top"] > grade.caixa["bottom"]]
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
            if nome in legenda:
                raise LegendaInvalidaError(f"rótulo repetido na legenda: {nome!r}")
            legenda[nome] = _assinatura(_imagem_pil(im))
        return legenda

    def validar(self, legenda):
        nomes = set(legenda)
        conhecidos = set(ROTULOS_MARCADORES)
        if nomes != conhecidos:
            faltam = sorted(conhecidos - nomes)
            sobram = sorted(nomes - conhecidos)
            raise LegendaInvalidaError(f"faltam {faltam}, sobram {sobram}")
        sem_imagem = sorted(n for n, img in legenda.items() if img is None)
        if sem_imagem:
            raise LegendaInvalidaError(
                f"ícone da legenda em formato não suportado: {sem_imagem}"
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
    # "Opção:" ("Mix de doces" / "Opção: Fruta") separa como "ou" e, como ele,
    # não entra na descrição do prato.
    return texto.lower() == "ou" or normalizar(texto) == "opcao:"


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

        - "ou"/"OU" separa pratos; "/" não separa (RF06.2). "Opção:" também
          separa e sai da descrição ("Opção: Fruta" vira "Fruta").
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
        """Marcador da legenda mais parecido com o ícone.

        Falha se o ícone estiver longe de todos (desconhecido) ou se o
        segundo colocado estiver perto demais do primeiro (ambíguo).
        """
        assinatura = _assinatura(icone["imagem"])
        if assinatura is None:
            raise AssociacaoFalhouError("ícone em formato de imagem não suportado")
        distancias = sorted(
            (_distancia(assinatura, ref), nome) for nome, ref in legenda.items()
        )
        (melhor, nome), (segunda, outro) = distancias[0], distancias[1]
        if melhor > DISTANCIA_MAX_ICONE:
            raise AssociacaoFalhouError(f"ícone desconhecido (distância {melhor:.1f})")
        # `<=` também pega o empate perfeito (0 contra 0).
        if segunda <= melhor * RAZAO_MIN_ICONE:
            raise AssociacaoFalhouError(
                f"ícone ambíguo entre {nome} ({melhor:.1f}) e {outro} ({segunda:.1f})"
            )
        return nome

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


def _dieta(nome_categoria):
    """Dieta da linha de prato principal ou complemento; None nas demais.

    None quer dizer "comum a todas as dietas" (RF09). Por isso, uma linha de
    prato principal com dieta desconhecida ("PRATO PRINCIPAL VEGANO") recusa
    o PDF, em vez de aparecer para todo mundo no filtro.
    """
    nome = normalizar(nome_categoria)
    if not nome.startswith(("prato principal", "complemento")):
        return None
    for chave, dieta in DIETAS.items():
        if nome.endswith(chave):
            return dieta
    raise FormatoPDFInvalidoError(f"linha de dieta desconhecida: {nome_categoria!r}")


def _ler_data(texto):
    """Dia da semana e data de uma célula do cabeçalho ("2ª FEIRA 21/9/2026").

    A data é dia/mês/ano, como nos PDFs, com ano de 4 ou 2 dígitos. Recusa
    datas que não existem e datas que não caem no dia da semana escrito
    acima delas (uma "2ª FEIRA 22/9/2026" é erro de digitação no PDF).
    """
    for token in texto.split():
        m = RE_DATA.match(token)
        if not m:
            continue
        d, mes, a = (int(g) for g in m.groups())
        if a < 100:
            a += 2000
        try:
            data = datetime.date(a, mes, d)
        except ValueError as e:
            raise FormatoPDFInvalidoError(f"data inválida no cabeçalho: {token}") from e
        dia = texto.split(token)[0].strip()
        esperado = DIAS_DA_SEMANA.get(normalizar(dia))
        if esperado is None:
            raise FormatoPDFInvalidoError(f"dia da semana desconhecido: {dia!r}")
        if data.weekday() != esperado:
            raise FormatoPDFInvalidoError(
                f"{dia} {token}: a data não cai nesse dia da semana"
            )
        return dia, data
    raise FormatoPDFInvalidoError(f"coluna do cabeçalho sem data: {texto!r}")


def _nome_refeicao(pagina, coluna):
    # Texto girado 90°: os caracteres ficam empilhados e se leem de baixo para cima.
    chars = [c for c in pagina.chars if _dentro(c, coluna) and c["text"].strip()]
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
        """Devolve (refeições, avisos).

        Falha de legenda ou de ícone numa página não derruba as outras: a
        página sai só em texto, com `alergenos_indisponiveis` e o motivo, e
        gera um aviso. Qualquer outra falha recusa o PDF inteiro.
        """
        resultados, avisos = [], []
        try:
            with pdfplumber.open(self.caminho) as pdf:
                for numero, pagina in enumerate(pdf.pages, start=1):
                    try:
                        refeicao = self._pagina(pagina)
                    except (LegendaInvalidaError, AssociacaoFalhouError) as e:
                        refeicao = self._pagina(pagina, com_marcadores=False)
                        refeicao.alergenos_indisponiveis = True
                        refeicao.motivo = f"{type(e).__name__}: {e}"
                        avisos.append(f"pág. {numero}: só em texto ({refeicao.motivo})")
                    except FormatoPDFInvalidoError as e:
                        raise FormatoPDFInvalidoError(f"pág. {numero}: {e}") from e
                    resultados.append(refeicao)
        except (OSError, PdfminerException, PSException) as e:
            raise FormatoPDFInvalidoError(f"não foi possível ler o PDF: {e}") from e
        return resultados, avisos

    def _pagina(self, pagina, com_marcadores=True):
        grade = Grade(pagina)

        def palavras_em(celula):
            # Palavras extraídas por célula: na página inteira, o pdfplumber
            # junta numa "linha" textos de alturas próximas em células
            # vizinhas e embaralha as letras de rótulos em fonte menor.
            return pagina.filter(lambda obj: _dentro(obj, celula)).extract_words(
                x_tolerance=1.5
            )

        # Cabeçalho: célula "COMPOSIÇÃO" define a coluna das categorias; as
        # colunas à direita, na mesma faixa, são os dias.
        cabecalho = [c for c in grade.celulas if c["linhas"][0] == 0]
        col_categoria = next(
            (
                c
                for c in cabecalho
                if ROTULO_COMPOSICAO in _texto(palavras_em(c)).upper()
            ),
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
            # Colunas sem texto são o espaço entre bordas duplas.
            if not texto:
                continue
            dia, data = _ler_data(texto)
            if any(d["data"] == data.isoformat() for d in dias):
                raise FormatoPDFInvalidoError(f"data repetida no cabeçalho: {data}")
            dias.append({"dia": dia, "data": data.isoformat(), "colunas": c["colunas"]})
        if not dias:
            raise FormatoPDFInvalidoError("nenhum dia no cabeçalho")

        icones, legenda = [], {}
        if com_marcadores:
            validador = LegendaValidator()
            legenda = validador.extrair(pagina, grade)
            validador.validar(legenda)
            legenda = {ROTULOS_MARCADORES[n]: img for n, img in legenda.items()}
            na_tabela = [im for im in pagina.images if _dentro(im, grade.caixa)]
            grandes = [
                im for im in na_tabela if im["bottom"] - im["top"] > ALTURA_MAX_ICONE
            ]
            if grandes:
                raise AssociacaoFalhouError(
                    f"{len(grandes)} imagem(ns) na tabela maiores que um ícone"
                )
            icones = [ic for im in na_tabela for ic in MarcadorIconMatcher.dividir(im)]

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
                for icone in icones:
                    if not _dentro(icone, celula):
                        continue
                    icones_usados.add(id(icone))
                    marcador = MarcadorIconMatcher.identificar(icone, legenda)
                    indice = MarcadorIconMatcher.associar(icone, grupos)
                    # O mesmo ícone repetido junto ao prato conta uma vez só.
                    if marcador not in pratos[indice].marcadores:
                        pratos[indice].marcadores.append(marcador)
                # Célula mesclada vale para todos os dias que ela cobre.
                cobertos = [
                    d
                    for d in dias
                    if celula["colunas"][0] <= d["colunas"][0]
                    and d["colunas"][1] <= celula["colunas"][1]
                ]
                if pratos and not cobertos:
                    raise FormatoPDFInvalidoError(
                        f"{nome}: célula com pratos fora das colunas de dias"
                    )
                for d in cobertos:
                    pratos_por_dia[d["data"]].extend(
                        PratoEstruturado(p.descricao, list(p.marcadores))
                        for p in pratos
                    )
            categorias.append(CategoriaEstruturada(nome, _dieta(nome), pratos_por_dia))

        soltos = [ic for ic in icones if id(ic) not in icones_usados]
        if soltos:
            raise AssociacaoFalhouError(
                f"{len(soltos)} ícone(s) fora das células de pratos"
            )

        return RefeicaoEstruturada(
            refeicao=_nome_refeicao(pagina, col_refeicao),
            dias=[{"dia": d["dia"], "data": d["data"]} for d in dias],
            categorias=categorias,
        )


def imprimir(refeicao):
    print(f"\n=== {refeicao.refeicao} ===")
    if refeicao.alergenos_indisponiveis:
        print(f"(sem marcadores: {refeicao.motivo})")
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
