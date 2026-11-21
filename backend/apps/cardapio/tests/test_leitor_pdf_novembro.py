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


def test_fazenda_agua_limpa_sem_jantar_como_no_pdf():
    refeicoes, avisos = _ler(FAZENDA_16_11)
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
