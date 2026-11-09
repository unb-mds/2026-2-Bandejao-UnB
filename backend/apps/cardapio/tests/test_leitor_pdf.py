"""Testes do leitor do PDF do cardápio (BE-04) com os PDFs reais.

Fixtures em fixtures/cardapios/:
- Gama, semana de 21 a 27/09/2026 (PDF gerado pelo Firefox, 5 ou 6 dias);
- Ceilândia e Darcy Ribeiro, semana de 09 a 15/11/2026 (PDFs gerados pelo
  Word, com ícones juntos numa imagem só; o Darcy tem domingo).

Os almoços esperados do Gama e do Darcy foram conferidos prato a prato e
ícone a ícone contra a imagem de cada página.
"""

import datetime
import re
from pathlib import Path
from types import SimpleNamespace

import pdfplumber
import pytest
from PIL import Image, ImageDraw

from apps.cardapio.leitor import cardapio_pdf_parser as leitor
from apps.cardapio.leitor.cardapio_pdf_parser import (
    AssociacaoFalhouError,
    CardapioEstruturador,
    CardapioPDFParser,
    FormatoPDFInvalidoError,
    Grade,
    LegendaInvalidaError,
    LegendaValidator,
    LeitorCardapioError,
    MarcadorIconMatcher,
)
from apps.cardapio.models import Dieta, TipoRefeicao

PASTA = Path(__file__).parent / "fixtures" / "cardapios"
GAMA = PASTA / "Gama-Semana-01-21-9-a-27-9.pdf"
CEILANDIA = PASTA / "Ceilandia-Semana-04-09-11-a-15-11.pdf"
DARCY = PASTA / "Darcy-Ribeiro-Semana-04-09-11-a-15-11.pdf"

# Nomes do MARCADOR no dicionário de dados do banco.
LEITE, OVO, SOJA, TRIGO = "leite_e_derivados", "ovo", "soja", "trigo_gluten"
SUINO, PIMENTA, AMENDOIM = "suino", "pimenta", "amendoim"
COGUMELO, OLEAGINOSA = "cogumelo", "oleaginosa"

# data -> categoria -> [(prato, {marcadores})]
GAMA_ALMOCO_ESPERADO = {
    "2026-09-21": {
        "SALADA 1": [("Repolho roxo", set())],
        "SALADA 2": [("Abobrinha ralada", set())],
        "MOLHO PARA SALADA": [("Chipotle", {PIMENTA})],
        "PRATO PRINCIPAL PADRÃO": [("Cubos de frango com manteiga de ervas", {LEITE})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Quibe de legumes com quinoa gratinado", {LEITE, TRIGO}),
            # DEFEITO CONHECIDO DO PDF, não comportamento desejado: este
            # "Limão" foi deixado por engano na célula (caso difícil 11). Foi
            # decidido em 08/11 não tratar; o teste só registra o que sai hoje.
            ("Limão", set()),
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Tomate recheado com quinoa", set())],
        "GUARNIÇÃO": [("Cenoura cozida", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Maçã", set())],
        "BEBIDA (Refresco de)": [("Jabuticaba", set())],
    },
    "2026-09-22": {
        "SALADA 1": [("Alface com chicória", set())],
        "SALADA 2": [("Tomate, cebola, pimentão em cubos", set())],
        "MOLHO PARA SALADA": [("Gengibre", {SOJA})],
        "PRATO PRINCIPAL PADRÃO": [("Carne de sol acebolada", {LEITE})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Bife de soja ao sugo gratinado", {SOJA, LEITE})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [
            ("Bolinho de feijão branco com couve", {TRIGO})
        ],
        "GUARNIÇÃO": [("Quibebe de mandioca", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Banana", set())],
        "BEBIDA (Refresco de)": [("Goiaba", set())],
    },
    "2026-09-23": {
        "SALADA 1": [("Mix de folhas", set())],
        "SALADA 2": [("Berinjela com pimentões", set())],
        "MOLHO PARA SALADA": [("Salsa", set())],
        "PRATO PRINCIPAL PADRÃO": [("Cubo de frango ao sugo", set())],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Risoto de ervilha com queijo", {LEITE, TRIGO})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [
            ("Refogado de ervilha, couve-flor e vagem", set())
        ],
        "GUARNIÇÃO": [("Legumes sauté (batata, chuchu e cenoura)", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Abacaxi", set())],
        "BEBIDA (Refresco de)": [("Caju", set())],
    },
    "2026-09-24": {
        "SALADA 1": [("Hakussai", {SOJA})],
        "SALADA 2": [("Beterraba ralada", set())],
        "MOLHO PARA SALADA": [("Ervas finas / Limão", set())],
        "PRATO PRINCIPAL PADRÃO": [("Suíno com cebola caramelizada", {SUINO})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Ovos mexidos com castanhas", {OVO, LEITE})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Soja xadrez", {SOJA, AMENDOIM})],
        "GUARNIÇÃO": [("Polenta com espinafre", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Mix de doces", {LEITE, AMENDOIM}), ("Fruta", set())],
        "BEBIDA (Refresco de)": [("Uva", set())],
    },
    "2026-09-25": {
        "SALADA 1": [("Couve-manteiga", set())],
        "SALADA 2": [("Abóbora ralada", set())],
        "MOLHO PARA SALADA": [("Vinagrete", set())],
        "PRATO PRINCIPAL PADRÃO": [("Feijoada", {SUINO, PIMENTA})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [("Omelete de vegetais", {OVO, LEITE})],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Feijoada Vegetariana", {SOJA})],
        "GUARNIÇÃO": [("Farofa de cebola", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Laranja", set())],
        "BEBIDA (Refresco de)": [("Morango", set())],
    },
    "2026-09-26": {
        "SALADA 1": [("Mostarda", set())],
        "SALADA 2": [("Tomate", set())],
        "MOLHO PARA SALADA": [("Alho e limão", set())],
        "PRATO PRINCIPAL PADRÃO": [
            ("Torta de carne com calabresa", {SUINO, TRIGO, LEITE})
        ],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Lasanha de espinafre gratinada", {LEITE, TRIGO, OVO})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Cuscuz vegetariano", {SOJA})],
        "GUARNIÇÃO": [("Seleta de legumes (cenoura, vagem e abobrinha)", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Melão", set())],
        "BEBIDA (Refresco de)": [("Tangerina", set())],
    },
}

DARCY_ALMOCO_ESPERADO = {
    "2026-11-09": {
        "SALADA 1": [("Alface roxa", set())],
        "SALADA 2": [("Caponata de berinjela", {COGUMELO})],
        "MOLHO PARA SALADA": [("Salsa", set())],
        "PRATO PRINCIPAL PADRÃO": [("Carne ao molho de vinho", {SOJA})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Berinjela recheada com quinoa gratinada", {LEITE})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Soja refogada com legumes", {SOJA})],
        "GUARNIÇÃO": [("Abóbora assada", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Laranja", set())],
        "BEBIDA (Refresco de)": [("Guaraná", set())],
    },
    "2026-11-10": {
        "SALADA 1": [("Acelga", set())],
        "SALADA 2": [("Tomate", set())],
        "MOLHO PARA SALADA": [("Chimichurri", set())],
        "PRATO PRINCIPAL PADRÃO": [("Lasanha de frango", {TRIGO, LEITE})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Bolinho de milho com soja gratinado", {LEITE, SOJA})
        ],
        # Três ícones encostados numa imagem só.
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Yakissoba", {AMENDOIM, SOJA, TRIGO})],
        "GUARNIÇÃO": [("Chuchu com vagem", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Mix de doces", {LEITE, AMENDOIM}), ("Frutas", set())],
        "BEBIDA (Refresco de)": [("Laranja", set())],
    },
    "2026-11-11": {
        "SALADA 1": [("Alface com mostarda", set())],
        "SALADA 2": [("Beterraba cozida", set())],
        "MOLHO PARA SALADA": [("Manjericão / Limão", set())],
        "PRATO PRINCIPAL PADRÃO": [("Suíno ao molho de bacon", {SUINO, SOJA})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Omelete de forno com manjericao e queijo gratinada", {LEITE, OVO})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [
            ("Abobrinha recheada com lentilha ao sugo", set())
        ],
        "GUARNIÇÃO": [("Mix de batatas assadas", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Banana", set())],
        "BEBIDA (Refresco de)": [("Maracujá", set())],
    },
    "2026-11-12": {
        "SALADA 1": [("Mix de folhas", set())],
        "SALADA 2": [("Tomate, cebola e pimentão em cubos", set())],
        "MOLHO PARA SALADA": [("Gengibre", {SOJA})],
        "PRATO PRINCIPAL PADRÃO": [("Silveirinha de carne", set())],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Suflê de batata", {LEITE, TRIGO, OVO})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [
            ("Quinoa com legumes refogados", set())
        ],
        "GUARNIÇÃO": [("Macarrão parafuso temperado", {TRIGO})],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Maçã", set())],
        "BEBIDA (Refresco de)": [("Uva", set())],
    },
    "2026-11-13": {
        "SALADA 1": [("Repolho branco com passas", set())],
        "SALADA 2": [("Cenoura ralada", set())],
        "MOLHO PARA SALADA": [("Hortelã / Limão", set())],
        "PRATO PRINCIPAL PADRÃO": [("Peixe ao molho de mostarda", {LEITE})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [("Ovos assados ao sugo", {OVO})],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Refogado de grão de bico", set())],
        "GUARNIÇÃO": [("Abobrinha refogada", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Melancia", set())],
        "BEBIDA (Refresco de)": [("Morango", set())],
    },
    "2026-11-14": {
        "SALADA 1": [("Alface lisa", set())],
        "SALADA 2": [("Pepino agridoce", set())],
        "MOLHO PARA SALADA": [("Ácido", set())],
        "PRATO PRINCIPAL PADRÃO": [("Frango assado com azeitonas", set())],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Fricassê de palmito com legumes", {TRIGO, LEITE, OVO})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Hambúrguer de soja assado", {SOJA})],
        "GUARNIÇÃO": [("Repolho com maçã e passas", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Abacaxi", set())],
        "BEBIDA (Refresco de)": [("Acerola", set())],
    },
    "2026-11-15": {
        "SALADA 1": [("Alface crespa com chicória", set())],
        "SALADA 2": [("Rabanete", set())],
        "MOLHO PARA SALADA": [("Chipotle", {PIMENTA})],
        "PRATO PRINCIPAL PADRÃO": [("Lagarto ao molho", {SOJA})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Almôndega de soja ao sugo gratinada", {LEITE, SOJA})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Charuto de soja ao sugo", {SOJA})],
        "GUARNIÇÃO": [("Milho refogado", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        "SOBREMESA": [("Melão", set())],
        "BEBIDA (Refresco de)": [("Manga", set())],
    },
}


def _ler(caminho):
    extraidas, avisos = CardapioPDFParser(str(caminho)).extrair()
    assert avisos == []
    assert not any(r.alergenos_indisponiveis for r in extraidas)
    return {r.refeicao: r for r in extraidas}


@pytest.fixture(scope="module")
def gama():
    return _ler(GAMA)


@pytest.fixture(scope="module")
def ceilandia():
    return _ler(CEILANDIA)


@pytest.fixture(scope="module")
def darcy():
    return _ler(DARCY)


def _como_dict(refeicao):
    # Lista ordenada, e não set: um marcador repetido no prato aparece.
    return {
        data: {
            cat.nome: [
                (p.descricao, sorted(p.marcadores)) for p in cat.pratos_por_dia[data]
            ]
            for cat in refeicao.categorias
            if cat.pratos_por_dia[data]
        }
        for data in (d["data"] for d in refeicao.dias)
    }


def _esperado(por_dia):
    return {
        data: {
            cat: [(nome, sorted(marcadores)) for nome, marcadores in pratos]
            for cat, pratos in categorias.items()
        }
        for data, categorias in por_dia.items()
    }


def _pratos(refeicao, categoria, data):
    cat = next(c for c in refeicao.categorias if c.nome == categoria)
    return [(p.descricao, p.marcadores) for p in cat.pratos_por_dia[data]]


# ------------------------------------------------------------------ Gama


def test_gama_le_as_tres_refeicoes_com_os_valores_do_model(gama):
    assert set(gama) == {"cafe", "almoco", "jantar"}


def test_gama_almoco_tem_seis_dias_e_o_cafe_cinco(gama):
    dias = [d["dia"] for d in gama["almoco"].dias]
    assert dias == [
        "2ª FEIRA",
        "3ª FEIRA",
        "4ª FEIRA",
        "5ª FEIRA",
        "6ª FEIRA",
        "SÁBADO",
    ]
    assert len(gama["cafe"].dias) == 5


def test_gama_almoco_completo_com_pratos_e_marcadores(gama):
    assert _como_dict(gama["almoco"]) == _esperado(GAMA_ALMOCO_ESPERADO)


def test_dieta_das_linhas_de_prato_principal_e_complemento(gama):
    dietas = {c.nome: c.dieta for c in gama["almoco"].categorias}
    assert dietas["PRATO PRINCIPAL PADRÃO"] == "padrao"
    assert dietas["PRATO PRINCIPAL OVOLACTOVEGETARIANO"] == "ovolacto"
    assert dietas["PRATO PRINCIPAL VEGETARIANO ESTRITO"] == "vegetariano_estrito"
    assert dietas["GUARNIÇÃO"] is None
    cafe = {c.nome: c.dieta for c in gama["cafe"].categorias}
    assert cafe["COMPLEMENTO VEGETARIANO ESTRITO"] == "vegetariano_estrito"


def test_celula_mesclada_vale_para_todos_os_dias(gama):
    bebidas = next(c for c in gama["cafe"].categorias if c.nome == "BEBIDAS")
    for pratos in bebidas.pratos_por_dia.values():
        assert [(p.descricao, p.marcadores) for p in pratos] == [
            ("Leite Integral", [LEITE]),
            ("Bebida de Soja", [SOJA]),
            ("Café", []),
            ("Chá", []),
        ]


def test_ou_no_fim_da_linha_separa_e_cada_pao_tem_seu_icone(gama):
    assert _pratos(gama["cafe"], "PANIFICAÇÃO", "2026-09-24") == [
        ("Pão francês", [TRIGO]),
        ("Pão careca", [TRIGO]),
    ]


def test_peixe_sem_marcador(gama):
    assert _pratos(gama["jantar"], "PRATO PRINCIPAL PADRÃO", "2026-09-23") == [
        ("Peixe ao molho de moqueca", [])
    ]


# ---------------------------------------------------------- Darcy Ribeiro


def test_darcy_almoco_completo_com_domingo(darcy):
    assert [d["dia"] for d in darcy["almoco"].dias][-2:] == ["SÁBADO", "DOMINGO"]
    assert _como_dict(darcy["almoco"]) == _esperado(DARCY_ALMOCO_ESPERADO)


def test_darcy_rotulo_em_fonte_menor_nao_embaralha(darcy):
    nomes = [c.nome for c in darcy["almoco"].categorias]
    assert "PRATO PRINCIPAL OVOLACTOVEGETARIANO" in nomes


def test_darcy_dois_icones_achatados_numa_imagem(darcy):
    assert _pratos(
        darcy["jantar"], "PRATO PRINCIPAL VEGETARIANO ESTRITO", "2026-11-11"
    ) == [("Strogonoff vegetariano", [SOJA, COGUMELO])]


def test_darcy_hifen_no_fim_da_linha_e_juntado(darcy):
    assert _pratos(darcy["cafe"], "COMPLEMENTO VEGETARIANO ESTRITO", "2026-11-15") == [
        ("Maionese de couve-flor", [])
    ]


def test_darcy_icones_de_um_prato_com_barra(darcy):
    assert _pratos(darcy["jantar"], "MOLHO PARA SALADA", "2026-11-09") == [
        ("Rosé / Limão", [LEITE, OVO])
    ]


# --------------------------------------------------------------- Ceilândia


def test_ceilandia_dias_por_refeicao(ceilandia):
    assert len(ceilandia["cafe"].dias) == 6
    assert len(ceilandia["almoco"].dias) == 6
    assert len(ceilandia["jantar"].dias) == 5


def test_ceilandia_linha_com_maiuscula_depois_de_conector_continua(ceilandia):
    assert _pratos(ceilandia["jantar"], "ACOMPANHAMENTOS", "2026-11-12") == [
        ("Arroz branco e Integral", []),
        ("Feijão preto", []),
    ]


def test_ceilandia_icone_de_legenda_em_jpeg(ceilandia):
    # O ícone de oleaginosa da legenda vem em JPEG (DCTDecode).
    assert _pratos(
        ceilandia["jantar"], "PRATO PRINCIPAL VEGETARIANO ESTRITO", "2026-11-12"
    ) == [("Moqueca de vegetais com ervilha, palmito e castanhas", [OLEAGINOSA])]


def test_ceilandia_tres_icones_encostados(ceilandia):
    assert _pratos(
        ceilandia["almoco"], "PRATO PRINCIPAL VEGETARIANO ESTRITO", "2026-11-10"
    ) == [("Yakissoba", [AMENDOIM, SOJA, TRIGO])]


# ------------------------------------------------- separar_pratos isolado


def _linhas(*textos):
    linhas = []
    for y, texto in enumerate(textos):
        linhas.append(
            [
                {
                    "text": t,
                    "x0": i * 10,
                    "x1": i * 10 + 8,
                    "top": y * 12,
                    "bottom": y * 12 + 10,
                }
                for i, t in enumerate(texto.split())
            ]
        )
    return linhas


def _descricoes(linhas):
    return [leitor._texto(g) for g in CardapioEstruturador.separar_pratos(linhas)]


def test_ou_separa_pratos():
    assert _descricoes(_linhas("Arroz branco OU arroz integral")) == [
        "Arroz branco",
        "arroz integral",
    ]


def test_barra_nao_separa():
    assert _descricoes(_linhas("Feijão carioca/preto")) == ["Feijão carioca/preto"]


def test_linha_com_minuscula_continua_o_prato():
    assert _descricoes(_linhas("Cubos de frango com", "manteiga de ervas")) == [
        "Cubos de frango com manteiga de ervas"
    ]


def test_linha_com_maiuscula_comeca_outro_prato():
    assert _descricoes(_linhas("Arroz branco e integral", "Feijão preto")) == [
        "Arroz branco e integral",
        "Feijão preto",
    ]


def test_linha_terminada_em_conector_continua_mesmo_com_maiuscula():
    assert _descricoes(_linhas("Arroz branco e", "Integral")) == [
        "Arroz branco e Integral"
    ]
    assert _descricoes(_linhas("Tomate, cebola,", "Pimentão")) == [
        "Tomate, cebola, Pimentão"
    ]


def test_opcao_separa_e_sai_da_descricao():
    assert _descricoes(_linhas("Mix de doces", "Opção: Fruta")) == [
        "Mix de doces",
        "Fruta",
    ]
    assert _descricoes(_linhas("Mix de doces", "OPÇÃO: Frutas")) == [
        "Mix de doces",
        "Frutas",
    ]


def test_ou_no_fim_da_linha():
    assert _descricoes(_linhas("Pão francês ou", "Pão careca ou", "Pão integral")) == [
        "Pão francês",
        "Pão careca",
        "Pão integral",
    ]


# ---------------------------------------------------------- legenda e ícones


def _legenda(cor=(255, 255, 255)):
    return {nome: Image.new("RGB", (24, 24), cor) for nome in leitor.ROTULOS_MARCADORES}


def test_legenda_com_os_dez_marcadores_e_valida():
    assert LegendaValidator().validar(_legenda()) is True


def test_legenda_sem_um_marcador_e_invalida():
    legenda = _legenda()
    del legenda["suino"]
    with pytest.raises(LegendaInvalidaError, match="suino"):
        LegendaValidator().validar(legenda)


def test_legenda_com_marcador_novo_e_invalida():
    legenda = _legenda()
    legenda["peixe"] = Image.new("RGB", (24, 24))
    with pytest.raises(LegendaInvalidaError, match="peixe"):
        LegendaValidator().validar(legenda)


def test_legenda_com_imagem_nao_decodificada_cita_o_marcador():
    legenda = _legenda()
    legenda["ovo"] = None
    with pytest.raises(LegendaInvalidaError, match="ovo"):
        LegendaValidator().validar(legenda)


def _legenda_cinza(perto):
    """Legenda em que só "mel" é branco; os outros nove são pretos."""
    legenda = {nome: Image.new("RGB", (24, 24), (0, 0, 0)) for nome in "abcdefghi"}
    legenda["mel"] = Image.new("RGB", (24, 24), (255, 255, 255))
    # Ícone cinza uniforme: a distância até o branco é 255 - nível.
    icone = {"imagem": Image.new("RGB", (52, 52), (255 - perto,) * 3)}
    return icone, legenda


def test_icone_logo_abaixo_do_limite_e_aceito():
    icone, legenda = _legenda_cinza(leitor.DISTANCIA_MAX_ICONE - 1)
    assert MarcadorIconMatcher.identificar(icone, legenda) == "mel"


def test_icone_logo_acima_do_limite_e_desconhecido():
    icone, legenda = _legenda_cinza(leitor.DISTANCIA_MAX_ICONE + 1)
    with pytest.raises(AssociacaoFalhouError, match="desconhecido"):
        MarcadorIconMatcher.identificar(icone, legenda)


def test_icone_ambiguo_falha_a_associacao():
    legenda = _legenda((0, 0, 255))
    legenda["mel"] = Image.new("RGB", (24, 24), (200, 0, 0))
    legenda["trigo/gluten"] = Image.new("RGB", (24, 24), (204, 0, 0))
    icone = {"imagem": Image.new("RGB", (52, 52), (202, 0, 0))}
    with pytest.raises(AssociacaoFalhouError, match="ambíguo"):
        MarcadorIconMatcher.identificar(icone, legenda)


def test_empate_perfeito_tambem_e_ambiguo():
    legenda = _legenda((0, 0, 255))
    legenda["mel"] = Image.new("RGB", (24, 24), (200, 0, 0))
    legenda["trigo/gluten"] = Image.new("RGB", (24, 24), (200, 0, 0))
    icone = {"imagem": Image.new("RGB", (52, 52), (200, 0, 0))}
    with pytest.raises(AssociacaoFalhouError, match="ambíguo"):
        MarcadorIconMatcher.identificar(icone, legenda)


def test_icone_em_formato_nao_suportado_falha_a_associacao():
    with pytest.raises(AssociacaoFalhouError):
        MarcadorIconMatcher.identificar({"imagem": None}, _legenda())


def test_icone_sem_prato_falha_a_associacao():
    icone = {"x0": 0, "x1": 10, "top": 0, "bottom": 10}
    with pytest.raises(AssociacaoFalhouError):
        MarcadorIconMatcher.associar(icone, [])


def test_imagem_cmyk_nao_e_lida_como_rgb():
    stream = SimpleNamespace(
        attrs={"Filter": None}, get_data=lambda: bytes(52 * 52 * 4)
    )
    cmyk = {"stream": stream, "colorspace": ["DeviceCMYK"], "srcsize": (52, 52)}
    assert leitor._imagem_pil({**cmyk, "bits": 8}) is None


def test_todas_as_excecoes_tem_a_mesma_base():
    for erro in (FormatoPDFInvalidoError, LegendaInvalidaError, AssociacaoFalhouError):
        assert issubclass(erro, LeitorCardapioError)


def test_valores_de_refeicao_e_dieta_existem_nos_models():
    assert set(leitor.REFEICOES.values()) == set(TipoRefeicao.values)
    assert set(leitor.DIETAS.values()) == set(Dieta.values)


def test_marcadores_seguem_o_dicionario_de_dados():
    assert set(leitor.ROTULOS_MARCADORES.values()) == {
        "cogumelo",
        "leite_e_derivados",
        "mel",
        "pimenta",
        "soja",
        "trigo_gluten",
        "amendoim",
        "oleaginosa",
        "ovo",
        "suino",
    }


# -------------------------------------------------- datas e dietas isoladas


def test_le_data_com_ano_de_quatro_ou_dois_digitos():
    assert leitor._ler_data("2ª FEIRA 21/9/2026") == (
        "2ª FEIRA",
        datetime.date(2026, 9, 21),
    )
    assert leitor._ler_data("SÁBADO 14/11/26") == (
        "SÁBADO",
        datetime.date(2026, 11, 14),
    )


def test_data_e_lida_como_dia_mes_ano():
    # 9 de novembro de 2026 é segunda; lida como mês/dia, seria 11 de setembro.
    assert leitor._ler_data("2ª FEIRA 09/11/2026")[1] == datetime.date(2026, 11, 9)


def test_dia_da_semana_por_extenso_tambem_e_aceito():
    assert leitor._ler_data("Segunda-feira 21/9/2026")[1] == datetime.date(2026, 9, 21)
    assert leitor._ler_data("DOMINGO 15/11/2026")[1] == datetime.date(2026, 11, 15)


def test_data_que_nao_cai_no_dia_da_semana_e_formato_invalido():
    with pytest.raises(FormatoPDFInvalidoError, match="não cai nesse dia da semana"):
        leitor._ler_data("2ª FEIRA 22/9/2026")


def test_dia_da_semana_desconhecido_e_formato_invalido():
    with pytest.raises(FormatoPDFInvalidoError, match="dia da semana desconhecido"):
        leitor._ler_data("FERIADO 21/9/2026")


def test_data_que_nao_existe_e_formato_invalido():
    with pytest.raises(FormatoPDFInvalidoError, match="data inválida"):
        leitor._ler_data("2ª FEIRA 31/02/2026")


def test_coluna_sem_data_e_formato_invalido():
    with pytest.raises(FormatoPDFInvalidoError, match="sem data"):
        leitor._ler_data("2ª FEIRA 21/09")


def test_linha_de_dieta_desconhecida_e_formato_invalido():
    assert leitor._dieta("GUARNIÇÃO") is None
    with pytest.raises(FormatoPDFInvalidoError, match="dieta desconhecida"):
        leitor._dieta("PRATO PRINCIPAL VEGANO")


# ------------------------------------- PDF real alterado: falhas que avisam


def _com_imagens_extras(monkeypatch, gerar):
    """Acrescenta imagens às páginas do PDF, como se viessem no arquivo.

    `gerar(numero_da_pagina, imagens)` devolve as imagens a acrescentar.
    """
    original = pdfplumber.page.Page.images

    def images(self):
        imagens = original.fget(self)
        if type(self) is not pdfplumber.page.Page:
            return imagens
        return imagens + gerar(self.page_number, imagens)

    monkeypatch.setattr(pdfplumber.page.Page, "images", property(images))


def _primeiro_icone_da_tabela(imagens):
    return next(im for im in imagens if 150 < im["top"] < 450 and im["x0"] > 180)


def _todos_os_marcadores(refeicao):
    return [
        m
        for cat in refeicao.categorias
        for pratos in cat.pratos_por_dia.values()
        for p in pratos
        for m in p.marcadores
    ]


def test_icone_fora_de_celula_de_prato_publica_a_pagina_so_em_texto(monkeypatch):
    def na_coluna_das_categorias(numero, imagens):
        if numero != 2:
            return []
        icone = _primeiro_icone_da_tabela(imagens)
        largura = icone["x1"] - icone["x0"]
        return [{**icone, "x0": 100, "x1": 100 + largura}]

    _com_imagens_extras(monkeypatch, na_coluna_das_categorias)
    refeicoes, avisos = CardapioPDFParser(str(GAMA)).extrair()
    almoco = refeicoes[1]
    assert almoco.alergenos_indisponiveis is True
    assert "fora das células" in almoco.motivo
    assert _todos_os_marcadores(almoco) == []
    # O texto continua lá, e as outras páginas não são afetadas.
    assert _pratos(almoco, "SALADA 1", "2026-09-21") == [("Repolho roxo", [])]
    assert refeicoes[0].alergenos_indisponiveis is False
    assert _todos_os_marcadores(refeicoes[2]) != []
    assert len(avisos) == 1 and avisos[0].startswith("pág. 2:")


def test_imagem_maior_que_icone_na_tabela_nao_some_em_silencio(monkeypatch):
    def icone_esticado(numero, imagens):
        if numero != 3:
            return []
        icone = _primeiro_icone_da_tabela(imagens)
        return [{**icone, "bottom": icone["top"] + leitor.ALTURA_MAX_ICONE + 5}]

    _com_imagens_extras(monkeypatch, icone_esticado)
    refeicoes, avisos = CardapioPDFParser(str(GAMA)).extrair()
    assert refeicoes[2].alergenos_indisponiveis is True
    assert "maiores que um ícone" in refeicoes[2].motivo
    assert _todos_os_marcadores(refeicoes[2]) == []
    assert len(avisos) == 1


def test_icone_repetido_junto_ao_prato_conta_uma_vez(monkeypatch):
    def repetido(numero, imagens):
        return [_primeiro_icone_da_tabela(imagens)] if numero == 2 else []

    _com_imagens_extras(monkeypatch, repetido)
    refeicoes, avisos = CardapioPDFParser(str(GAMA)).extrair()
    assert avisos == []
    assert _como_dict(refeicoes[1]) == _esperado(GAMA_ALMOCO_ESPERADO)


def test_pdf_sem_datas_reconhecidas_e_recusado(monkeypatch):
    monkeypatch.setattr(leitor, "RE_DATA", re.compile(r"^nunca$"))
    with pytest.raises(FormatoPDFInvalidoError, match="pág. 1: coluna do cabeçalho"):
        CardapioPDFParser(str(GAMA)).extrair()


def _apagar_textos(monkeypatch, padrao):
    """Faz o leitor ver como vazias as células cujo texto casa com `padrao`."""
    original = leitor._texto

    def texto(palavras):
        lido = original(palavras)
        return "" if re.search(padrao, lido) else lido

    monkeypatch.setattr(leitor, "_texto", texto)


def test_cabecalho_sem_nenhum_dia_e_recusado(monkeypatch):
    _apagar_textos(monkeypatch, r"\d+/\d+/\d+")
    with pytest.raises(FormatoPDFInvalidoError, match="nenhum dia"):
        CardapioPDFParser(str(GAMA)).extrair()


def test_celula_com_pratos_fora_dos_dias_e_recusada(monkeypatch):
    # Some só o cabeçalho da 3ª feira: os pratos dela ficam sem dia.
    _apagar_textos(monkeypatch, r"22/9/2026")
    with pytest.raises(FormatoPDFInvalidoError, match="fora das colunas de dias"):
        CardapioPDFParser(str(GAMA)).extrair()


def test_rotulo_repetido_na_legenda_publica_so_em_texto(monkeypatch):
    original = leitor.normalizar
    monkeypatch.setattr(
        leitor,
        "normalizar",
        lambda texto: "pimenta" if original(texto) == "mel" else original(texto),
    )
    refeicoes, avisos = CardapioPDFParser(str(GAMA)).extrair()
    assert all(r.alergenos_indisponiveis for r in refeicoes)
    assert all("repetido" in r.motivo for r in refeicoes)
    assert len(avisos) == 3


def test_formato_invalido_na_releitura_so_em_texto_diz_a_pagina(monkeypatch):
    # Legenda ruim (rótulo repetido) e dieta desconhecida na mesma página: a
    # releitura sem marcadores recusa o PDF, e a mensagem ainda diz a página.
    original = leitor.normalizar
    monkeypatch.setattr(
        leitor,
        "normalizar",
        lambda texto: "pimenta" if original(texto) == "mel" else original(texto),
    )
    dietas = {k: v for k, v in leitor.DIETAS.items() if k != "padrao"}
    monkeypatch.setattr(leitor, "DIETAS", dietas)
    with pytest.raises(FormatoPDFInvalidoError, match=r"^pág\. 1: linha de dieta"):
        CardapioPDFParser(str(GAMA)).extrair()


def test_data_repetida_no_cabecalho_e_recusada(monkeypatch):
    monkeypatch.setattr(
        leitor, "_ler_data", lambda texto: ("2ª FEIRA", datetime.date(2026, 9, 21))
    )
    with pytest.raises(FormatoPDFInvalidoError, match="data repetida"):
        CardapioPDFParser(str(GAMA)).extrair()


def test_pdf_sem_coluna_composicao_e_recusado(monkeypatch):
    monkeypatch.setattr(leitor, "ROTULO_COMPOSICAO", "NAO EXISTE")
    with pytest.raises(FormatoPDFInvalidoError, match="COMPOSIÇÃO"):
        CardapioPDFParser(str(GAMA)).extrair()


def test_refeicao_desconhecida_e_recusada(monkeypatch):
    monkeypatch.setattr(leitor, "REFEICOES", {})
    with pytest.raises(FormatoPDFInvalidoError, match="refeição desconhecida"):
        CardapioPDFParser(str(GAMA)).extrair()


def test_arquivo_que_nao_e_pdf_e_formato_invalido(tmp_path):
    pagina_de_erro = tmp_path / "cardapio.pdf"
    pagina_de_erro.write_text("<html><body>Erro 503</body></html>")
    with pytest.raises(FormatoPDFInvalidoError, match="não foi possível ler"):
        CardapioPDFParser(str(pagina_de_erro)).extrair()


def test_arquivo_inexistente_e_formato_invalido(tmp_path):
    with pytest.raises(FormatoPDFInvalidoError):
        CardapioPDFParser(str(tmp_path / "nao-existe.pdf")).extrair()


def _aneis(posicoes, largura, altura=52):
    img = Image.new("RGB", (largura, altura), (255, 255, 255))
    desenho = ImageDraw.Draw(img)
    for x in posicoes:
        desenho.ellipse(
            (x, 1, x + altura - 3, altura - 2), outline=(0, 120, 0), width=4
        )
    return img


def test_faixas_separam_icones_com_espaco_entre_eles():
    assert len(leitor._faixas_com_tinta(_aneis([1, 60], 112))) == 2


def test_faixas_dividem_icones_encostados_pela_proporcao():
    assert len(leitor._faixas_com_tinta(_aneis([0, 52, 104], 156))) == 3


def test_tabela_sem_bordas_e_formato_invalido():
    pagina_sem_bordas = SimpleNamespace(rects=[])
    with pytest.raises(FormatoPDFInvalidoError):
        Grade(pagina_sem_bordas)


def test_main_imprime_as_refeicoes(capsys):
    assert leitor.main(["leitor", str(GAMA)]) == 0
    saida = capsys.readouterr().out
    assert "=== almoco ===" in saida
    assert "Chipotle  <pimenta>" in saida
    assert "AVISO" not in saida


def test_main_em_json(capsys):
    assert leitor.main(["leitor", str(GAMA), "--json"]) == 0
    assert '"refeicao": "jantar"' in capsys.readouterr().out


def test_main_sem_arquivo_mostra_o_uso(capsys):
    assert leitor.main(["leitor"]) == 2
    assert "Uso" in capsys.readouterr().out
