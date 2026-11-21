"""Testes do leitor com os PDFs publicados pelo RU em novembro de 2026 (BE-12).

Fixtures em fixtures/cardapios/, baixadas da página do RU em 21/11/2026:
- Gama, semanas de 16/11 (5 dias) e de 23/11;
- Fazenda Água Limpa, semana de 16/11 (café e almoço, sem jantar);
- Planaltina, semana de 23/11 (campus nunca testado no BE-04).

Desde a semana de 16/11, o cabeçalho traz a data entre parênteses, numa
linha abaixo do dia: "2ª FEIRA (16/11/2026)" (caso 26 do BE-04). Os valores
esperados foram conferidos contra a imagem de cada página.
"""

from pathlib import Path

import pytest

from apps.cardapio.leitor.cardapio_pdf_parser import CardapioPDFParser

PASTA = Path(__file__).parent / "fixtures" / "cardapios"
GAMA_16_11 = PASTA / "Gama-Semana-01-16-11-a-20-11-1.pdf"
GAMA_23_11 = PASTA / "Gama-Semana-02-23-11-a-29-11.pdf"
FAZENDA_16_11 = PASTA / "Fazenda-Semana-01-16-11-a-20-11-2.pdf"
PLANALTINA_23_11 = PASTA / "Planaltina-Semana-02-23-11-a-29-11.pdf"

SEMANA_16_11 = ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]


def _ler(caminho):
    refeicoes, avisos = CardapioPDFParser(str(caminho)).extrair()
    return {r.refeicao: r for r in refeicoes}, avisos


@pytest.fixture(scope="module")
def gama():
    return _ler(GAMA_16_11)


def _datas(refeicao):
    return [d["data"] for d in refeicao.dias]


def test_gama_16_11_com_a_data_entre_parenteses_e_lido(gama):
    refeicoes, _ = gama
    assert set(refeicoes) == {"cafe", "almoco", "jantar"}
    for refeicao in refeicoes.values():
        assert _datas(refeicao) == SEMANA_16_11
        assert [d["dia"] for d in refeicao.dias] == [
            "2ª FEIRA",
            "3ª FEIRA",
            "4ª FEIRA",
            "5ª FEIRA",
            "6ª FEIRA",
        ]


def test_gama_16_11_cafe_e_jantar_saem_com_marcadores(gama):
    refeicoes, _ = gama
    assert refeicoes["cafe"].alergenos_indisponiveis is False
    assert refeicoes["jantar"].alergenos_indisponiveis is False


# Nomes do MARCADOR no dicionário de dados do banco.
LEITE, OVO, SOJA, TRIGO = "leite_e_derivados", "ovo", "soja", "trigo_gluten"
SUINO, PIMENTA, AMENDOIM = "suino", "pimenta", "amendoim"

# data -> categoria -> [(prato, {marcadores})], conferido contra a imagem da
# página 2 do PDF do Gama de 16/11 (o mesmo almoço do PDF da Fazenda).
GAMA_ALMOCO_16_11 = {
    "2026-11-16": {
        "SALADA 1": [("Repolho roxo", set())],
        "SALADA 2": [("Abobrinha ralada", set())],
        "MOLHO PARA SALADA": [("Chipotle / Limão", {PIMENTA})],
        "PRATO PRINCIPAL PADRÃO": [("Frango com creme de milho", {LEITE})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Quibe de legumes com quinoa gratinado", {LEITE, TRIGO})
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
    "2026-11-17": {
        "SALADA 1": [("Alface com chicória", set())],
        "SALADA 2": [("Tomate, cebola, pimentão em cubos", set())],
        "MOLHO PARA SALADA": [("Gengibre /Limão", {SOJA})],
        "PRATO PRINCIPAL PADRÃO": [("Suíno com cebola caramelizada", {SUINO})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Ovos mexidos com castanhas", {OVO, LEITE})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [
            ("Bolinho de feijão branco com couve", {TRIGO})
        ],
        "GUARNIÇÃO": [("Quibebe de mandioca", set())],
        # DEFEITO CONHECIDO DO PDF (caso 12 do BE-04, palavras na mesma
        # linha): no PDF, "Feijão" está na linha do arroz e "carioca" na de
        # baixo, então os dois pratos saem como um só.
        "ACOMPANHAMENTOS": [("Arroz branco e integral Feijão carioca", set())],
        "SOBREMESA": [("Banana", set())],
        "BEBIDA (Refresco de)": [("Goiaba", set())],
    },
    "2026-11-18": {
        "SALADA 1": [("Mix de folhas", set())],
        "SALADA 2": [("Berinjela com pimentões", set())],
        "MOLHO PARA SALADA": [("Salsa", set())],
        "PRATO PRINCIPAL PADRÃO": [("Coxa e sobrecoxa ao molho manjericão", set())],
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
    "2026-11-19": {
        "SALADA 1": [("Hakussai", {SOJA})],
        "SALADA 2": [("Beterraba ralada", set())],
        "MOLHO PARA SALADA": [("Ervas finas / Limão", set())],
        "PRATO PRINCIPAL PADRÃO": [("Lagarto ao molho escuro", {SOJA})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Bife de soja ao sugo gratinado", {SOJA, LEITE})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Soja xadrez", {SOJA, AMENDOIM})],
        "GUARNIÇÃO": [("Polenta com espinafre", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão carioca", set()),
        ],
        # Os ícones de leite e amendoim colados numa imagem só (caso 27).
        "SOBREMESA": [("Mix de doces", {LEITE, AMENDOIM}), ("Fruta", set())],
        "BEBIDA (Refresco de)": [("Uva", set())],
    },
    "2026-11-20": {
        "SALADA 1": [("Couve-manteiga", set())],
        "SALADA 2": [("Abóbora ralada", set())],
        "MOLHO PARA SALADA": [("Vinagrete", set())],
        "PRATO PRINCIPAL PADRÃO": [("Feijoada", {SUINO, PIMENTA})],
        "PRATO PRINCIPAL OVOLACTOVEGETARIANO": [
            ("Omelete de vegetais com queijo gartinada", {OVO, LEITE})
        ],
        "PRATO PRINCIPAL VEGETARIANO ESTRITO": [("Feijoada Vegetariana", {SOJA})],
        "GUARNIÇÃO": [("Farofa de cebola", set())],
        "ACOMPANHAMENTOS": [
            ("Arroz branco e integral", set()),
            ("Feijão preto", set()),
        ],
        "SOBREMESA": [("Laranja", set())],
        "BEBIDA (Refresco de)": [("Morango", set())],
    },
}


def _como_dict(refeicao):
    return {
        data: {
            cat.nome: [
                (p.descricao, sorted(p.marcadores)) for p in cat.pratos_por_dia[data]
            ]
            for cat in refeicao.categorias
            if cat.pratos_por_dia[data]
        }
        for data in _datas(refeicao)
    }


def _esperado(por_dia):
    return {
        data: {
            cat: [(nome, sorted(marcadores)) for nome, marcadores in pratos]
            for cat, pratos in categorias.items()
        }
        for data, categorias in por_dia.items()
    }


def test_gama_16_11_sai_sem_avisos(gama):
    refeicoes, avisos = gama
    assert avisos == []
    assert not any(r.alergenos_indisponiveis for r in refeicoes.values())


def test_gama_16_11_almoco_completo_com_os_icones_encostados(gama):
    refeicoes, _ = gama
    assert _como_dict(refeicoes["almoco"]) == _esperado(GAMA_ALMOCO_16_11)


def test_fazenda_16_11_almoco_igual_ao_do_gama_e_com_marcadores():
    refeicoes, avisos = _ler(FAZENDA_16_11)
    assert avisos == []
    sobremesa = next(c for c in refeicoes["almoco"].categorias if c.nome == "SOBREMESA")
    assert [
        (p.descricao, sorted(p.marcadores))
        for p in sobremesa.pratos_por_dia["2026-11-19"]
    ] == [("Mix de doces", [AMENDOIM, LEITE]), ("Fruta", [])]


def test_fazenda_agua_limpa_sem_jantar_como_no_pdf():
    refeicoes, _ = _ler(FAZENDA_16_11)
    assert set(refeicoes) == {"cafe", "almoco"}
    assert _datas(refeicoes["almoco"]) == SEMANA_16_11


def _pratos(refeicao, categoria, data):
    cat = next(c for c in refeicao.categorias if c.nome == categoria)
    return [(p.descricao, sorted(p.marcadores)) for p in cat.pratos_por_dia[data]]


def test_planaltina_23_11_e_lido_com_os_sete_dias():
    refeicoes, avisos = _ler(PLANALTINA_23_11)
    assert avisos == []
    assert set(refeicoes) == {"cafe", "almoco", "jantar"}
    for refeicao in refeicoes.values():
        assert _datas(refeicao) == [f"2026-11-{dia}" for dia in range(23, 30)]
    almoco = refeicoes["almoco"]
    assert [d["dia"] for d in almoco.dias][-2:] == ["SÁBADO", "DOMINGO"]
    assert _pratos(almoco, "PRATO PRINCIPAL PADRÃO", "2026-11-25") == [
        ("Lasanha à bolonhesa", ["leite_e_derivados", "suino", "trigo_gluten"])
    ]
    assert _pratos(almoco, "SOBREMESA", "2026-11-24") == [
        ("Mix de doces", ["amendoim", "leite_e_derivados"]),
        ("Fruta", []),
    ]


def test_gama_23_11_e_lido_sem_avisos():
    refeicoes, avisos = _ler(GAMA_23_11)
    assert avisos == []
    assert _datas(refeicoes["almoco"])[0] == "2026-11-23"
