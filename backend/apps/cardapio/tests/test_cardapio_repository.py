"""Testes do CardapioRepository: gravação do cardápio lido do PDF (BE-12, C4 4b).

A refeição gravada sai do PDF real do Gama de 16/11 (o mesmo da
test_leitor_pdf_novembro), e os campi e os marcadores vêm das fixtures da
BD-03. Os valores esperados (ordem, dieta, marcadores) são os da imagem do
PDF, não os da saída do código.
"""

import logging
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from apps.avaliacao.models import Avaliacao
from apps.cardapio.leitor.cardapio_downloader import FontePDF
from apps.cardapio.leitor.cardapio_pdf_parser import (
    CardapioPDFParser,
    CategoriaEstruturada,
    PratoEstruturado,
    RefeicaoEstruturada,
)
from apps.cardapio.leitor.cardapio_repository import CardapioRepository
from apps.cardapio.models import (
    Campus,
    Categoria,
    Marcador,
    Prato,
    PratoMarcador,
    Refeicao,
    StatusLeitura,
)

PDF = (
    Path(__file__).parent
    / "fixtures"
    / "cardapios"
    / "Gama-Semana-01-16-11-a-20-11-1.pdf"
)
URL = "https://ru.unb.br/wp-content/uploads/2026/11/Gama-Semana-01-16-11-a-20-11-1.pdf"
BRASILIA = ZoneInfo("America/Sao_Paulo")
DIAS = [date(2026, 11, d) for d in range(16, 21)]


@pytest.fixture(scope="module")
def lidas():
    refeicoes, avisos = CardapioPDFParser(str(PDF)).extrair()
    assert avisos == []
    return {r.refeicao: r for r in refeicoes}


@pytest.fixture
def gama(db):
    call_command("loaddata", "campi", "marcadores", verbosity=0)
    return Campus.objects.get(nome="Gama")


def _fonte(campus, url=URL):
    return FontePDF(
        campus,
        url,
        "ISM – 16/11/2026 À 22/11/2026",
        date(2026, 11, 16),
        date(2026, 11, 22),
    )


def _cardapio(refeicao):
    """categoria -> [(prato, dieta, {marcadores})], na ordem gravada."""
    return [
        (
            categoria.nome,
            [
                (prato.nome, prato.dieta, {m.nome for m in prato.marcadores.all()})
                for prato in categoria.pratos.order_by("ordem")
            ],
        )
        for categoria in refeicao.categorias.order_by("ordem")
    ]


# ------------------------------------------------------------------ salvar


def test_salvar_grava_uma_refeicao_por_dia_com_horario_e_fonte(gama, lidas):
    CardapioRepository().salvar(gama, _fonte(gama), lidas["almoco"])
    refeicoes = Refeicao.objects.filter(campus=gama).order_by("data")
    assert [(r.data, r.tipo) for r in refeicoes] == [(d, "almoco") for d in DIAS]
    for refeicao in refeicoes:
        # Anexo A: almoço das 11h às 14h30.
        assert (refeicao.horario_inicio, refeicao.horario_fim) == (
            time(11, 0),
            time(14, 30),
        )
        assert refeicao.status_leitura == StatusLeitura.OK
        assert refeicao.fonte_pdf_url == URL


def test_salvar_grava_categorias_e_pratos_na_ordem_do_pdf(gama, lidas):
    CardapioRepository().salvar(gama, _fonte(gama), lidas["almoco"])
    quinta = Refeicao.objects.get(campus=gama, data=date(2026, 11, 19), tipo="almoco")
    assert _cardapio(quinta) == [
        ("SALADA 1", [("Hakussai", None, {"soja"})]),
        ("SALADA 2", [("Beterraba ralada", None, set())]),
        ("MOLHO PARA SALADA", [("Ervas finas / Limão", None, set())]),
        ("PRATO PRINCIPAL PADRÃO", [("Lagarto ao molho escuro", "padrao", {"soja"})]),
        (
            "PRATO PRINCIPAL OVOLACTOVEGETARIANO",
            [
                (
                    "Bife de soja ao sugo gratinado",
                    "ovolacto",
                    {"soja", "leite_e_derivados"},
                )
            ],
        ),
        (
            "PRATO PRINCIPAL VEGETARIANO ESTRITO",
            [("Soja xadrez", "vegetariano_estrito", {"soja", "amendoim"})],
        ),
        ("GUARNIÇÃO", [("Polenta com espinafre", None, set())]),
        (
            "ACOMPANHAMENTOS",
            [("Arroz branco e integral", None, set()), ("Feijão carioca", None, set())],
        ),
        (
            "SOBREMESA",
            [
                # Os ícones encostados do caso 27: leite e amendoim.
                ("Mix de doces", None, {"leite_e_derivados", "amendoim"}),
                ("Fruta", None, set()),
            ],
        ),
        ("BEBIDA (Refresco de)", [("Uva", None, set())]),
    ]


def test_ordem_das_categorias_segue_a_posicao_no_pdf(gama, lidas):
    CardapioRepository().salvar(gama, _fonte(gama), lidas["almoco"])
    ordens = list(
        Categoria.objects.filter(refeicao__data=date(2026, 11, 16))
        .order_by("ordem")
        .values_list("nome", "ordem")
    )
    assert [nome for nome, _ in ordens][:3] == [
        "SALADA 1",
        "SALADA 2",
        "MOLHO PARA SALADA",
    ]
    assert [ordem for _, ordem in ordens] == sorted({ordem for _, ordem in ordens})


def test_dieta_da_categoria_e_copiada_para_cada_prato(gama):
    estruturada = RefeicaoEstruturada(
        refeicao="jantar",
        dias=[{"dia": "2ª FEIRA", "data": "2026-11-16"}],
        categorias=[
            CategoriaEstruturada(
                "PRATO PRINCIPAL OVOLACTOVEGETARIANO",
                "ovolacto",
                {
                    "2026-11-16": [
                        PratoEstruturado("Omelete"),
                        PratoEstruturado("Quiche"),
                    ]
                },
            )
        ],
    )
    CardapioRepository().salvar(gama, _fonte(gama), estruturada)
    assert list(Prato.objects.values_list("nome", "dieta", "ordem")) == [
        ("Omelete", "ovolacto", 0),
        ("Quiche", "ovolacto", 1),
    ]


def test_categoria_sem_prato_no_dia_nao_e_gravada(gama):
    estruturada = RefeicaoEstruturada(
        refeicao="almoco",
        dias=[
            {"dia": "2ª FEIRA", "data": "2026-11-16"},
            {"dia": "3ª FEIRA", "data": "2026-11-17"},
        ],
        categorias=[
            CategoriaEstruturada(
                "SALADA 1",
                None,
                {
                    "2026-11-16": [PratoEstruturado("Alface")],
                    "2026-11-17": [PratoEstruturado("Tomate")],
                },
            ),
            CategoriaEstruturada(
                "OPÇÃO EXTRA",
                None,
                {
                    "2026-11-16": [],
                    "2026-11-17": [PratoEstruturado("Cuscuz")],
                },
            ),
        ],
    )
    CardapioRepository().salvar(gama, _fonte(gama), estruturada)
    por_dia = {
        r.data.day: [c.nome for c in r.categorias.order_by("ordem")]
        for r in Refeicao.objects.all()
    }
    assert por_dia == {16: ["SALADA 1"], 17: ["SALADA 1", "OPÇÃO EXTRA"]}


def test_marcador_desconhecido_e_erro_e_nao_e_ignorado(gama):
    estruturada = RefeicaoEstruturada(
        refeicao="almoco",
        dias=[{"dia": "2ª FEIRA", "data": "2026-11-16"}],
        categorias=[
            CategoriaEstruturada(
                "SALADA 1",
                None,
                {"2026-11-16": [PratoEstruturado("Alface", ["gergelim"])]},
            )
        ],
    )
    with pytest.raises(Marcador.DoesNotExist):
        CardapioRepository().salvar(gama, _fonte(gama), estruturada)


# ------------------------------------------------------------- releitura


def _criar_avaliacao(usuario, refeicao):
    return Avaliacao.objects.create(usuario=usuario, refeicao=refeicao, nota=5)


def test_releitura_atualiza_a_refeicao_e_mantem_a_avaliacao(gama, lidas, usuario):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    segunda = Refeicao.objects.get(campus=gama, data=DIAS[0], tipo="almoco")
    avaliacao = _criar_avaliacao(usuario, segunda)

    nova_url = URL.replace("-1.pdf", "-2.pdf")
    repositorio.salvar(gama, _fonte(gama, nova_url), lidas["almoco"])

    # Mesma linha (não houve CASCADE), com a URL nova e sem pratos repetidos.
    relida = Refeicao.objects.get(pk=segunda.pk)
    assert relida.fonte_pdf_url == nova_url
    assert Avaliacao.objects.filter(pk=avaliacao.pk, refeicao=relida).exists()
    assert Refeicao.objects.filter(campus=gama).count() == 5
    assert relida.categorias.count() == 10
    assert Prato.objects.filter(categoria__refeicao=relida).count() == 11


def test_releitura_troca_os_pratos_e_os_marcadores(gama, lidas):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    corrigida = RefeicaoEstruturada(
        refeicao="almoco",
        dias=[{"dia": "2ª FEIRA", "data": "2026-11-16"}],
        categorias=[
            CategoriaEstruturada(
                "SALADA 1", None, {"2026-11-16": [PratoEstruturado("Rúcula", ["mel"])]}
            )
        ],
    )
    repositorio.salvar(gama, _fonte(gama), corrigida)
    segunda = Refeicao.objects.get(campus=gama, data=DIAS[0], tipo="almoco")
    assert _cardapio(segunda) == [("SALADA 1", [("Rúcula", None, {"mel"})])]
    # Os pratos antigos e os vínculos com marcadores sumiram de vez.
    assert not Prato.objects.filter(categoria__refeicao=segunda, nome="Repolho roxo")
    assert PratoMarcador.objects.filter(prato__categoria__refeicao=segunda).count() == 1


def test_releitura_de_refeicao_so_em_texto_volta_para_ok(gama, lidas):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    repositorio.marcar_alergenos_indisponivel(gama, "almoco", DIAS[0])
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    segunda = Refeicao.objects.get(campus=gama, data=DIAS[0], tipo="almoco")
    assert segunda.status_leitura == StatusLeitura.OK


# --------------------------------------------- marcar_alergenos_indisponivel


def test_marcar_alergenos_indisponivel_muda_so_aquela_refeicao(gama, lidas):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    repositorio.salvar(gama, _fonte(gama), lidas["jantar"])
    repositorio.marcar_alergenos_indisponivel(gama, "almoco", DIAS[2])
    status = {
        (r.data, r.tipo): r.status_leitura for r in Refeicao.objects.filter(campus=gama)
    }
    assert status.pop((DIAS[2], "almoco")) == StatusLeitura.ALERGENOS_INDISPONIVEIS
    assert set(status.values()) == {StatusLeitura.OK}
    assert Refeicao.objects.get(
        campus=gama, data=DIAS[2], tipo="almoco"
    ).alergenos_indisponivel


def test_pagina_so_em_texto_grava_pratos_sem_marcadores(gama):
    so_texto = RefeicaoEstruturada(
        refeicao="almoco",
        dias=[{"dia": "2ª FEIRA", "data": "2026-11-16"}],
        categorias=[
            CategoriaEstruturada(
                "SOBREMESA", None, {"2026-11-16": [PratoEstruturado("Mix de doces")]}
            )
        ],
        alergenos_indisponiveis=True,
        motivo="AssociacaoFalhouError: ícone desconhecido",
    )
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), so_texto)
    repositorio.marcar_alergenos_indisponivel(gama, "almoco", DIAS[0])
    segunda = Refeicao.objects.get(campus=gama, data=DIAS[0], tipo="almoco")
    assert segunda.status_leitura == StatusLeitura.ALERGENOS_INDISPONIVEIS
    assert _cardapio(segunda) == [("SOBREMESA", [("Mix de doces", None, set())])]


# ------------------------------------------------------ manter_ultimo_valido


def test_manter_ultimo_valido_nao_toca_no_banco(gama, lidas, django_assert_num_queries):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    antes = list(Refeicao.objects.values_list("pk", "lida_em", "status_leitura"))
    with django_assert_num_queries(1):
        # Só uma consulta, para dizer se há cardápio anterior da semana.
        repositorio.manter_ultimo_valido(gama, _fonte(gama))
    assert (
        list(Refeicao.objects.values_list("pk", "lida_em", "status_leitura")) == antes
    )
    # Nunca cria linha `leitura_falhou` (decisão P2).
    assert not Refeicao.objects.filter(status_leitura=StatusLeitura.LEITURA_FALHOU)


def test_manter_ultimo_valido_diz_se_havia_cardapio_da_semana(gama):
    from apps.cardapio.models import FonteCardapio

    repositorio = CardapioRepository()
    assert repositorio.manter_ultimo_valido(gama, _fonte(gama)) is False
    agora = datetime(2026, 11, 16, 9, 0, tzinfo=BRASILIA)
    FonteCardapio.objects.create(
        campus=gama,
        semana_inicio=date(2026, 11, 16),
        url=URL,
        sha256="0" * 64,
        verificado_em=agora,
        processado_em=agora,
    )
    assert repositorio.manter_ultimo_valido(gama, _fonte(gama)) is True
    assert not Refeicao.objects.exists()


# ------------------------------------------ refeições que sumiram (P1)


def _sem_o_jantar_de_sexta(jantar):
    return RefeicaoEstruturada(
        refeicao=jantar.refeicao,
        dias=[d for d in jantar.dias if d["data"] != "2026-11-20"],
        categorias=jantar.categorias,
    )


def test_refeicao_que_sumiu_do_pdf_e_apagada(gama, lidas):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["jantar"])
    corrigido = _sem_o_jantar_de_sexta(lidas["jantar"])
    gravadas = repositorio.salvar(gama, _fonte(gama), corrigido)
    repositorio.remover_ausentes(gama, _fonte(gama), gravadas)
    assert sorted(Refeicao.objects.values_list("data", flat=True)) == DIAS[:4]


def test_refeicao_que_sumiu_mas_tem_avaliacao_fica_com_aviso(
    gama, lidas, usuario, caplog
):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["jantar"])
    sexta = Refeicao.objects.get(campus=gama, data=DIAS[4], tipo="jantar")
    _criar_avaliacao(usuario, sexta)
    corrigido = _sem_o_jantar_de_sexta(lidas["jantar"])
    gravadas = repositorio.salvar(gama, _fonte(gama), corrigido)
    with caplog.at_level(logging.WARNING):
        mantidas = repositorio.remover_ausentes(gama, _fonte(gama), gravadas)
    assert mantidas == [sexta]
    assert Refeicao.objects.filter(pk=sexta.pk).exists()
    assert Avaliacao.objects.filter(refeicao=sexta).count() == 1
    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 1
    mensagem = avisos[0].getMessage()
    assert (
        str(gama.pk) in mensagem and "2026-11-20" in mensagem and "jantar" in mensagem
    )
    # Nenhum dado de usuário no log.
    assert usuario.email_institucional not in mensagem


def test_refeicao_mantida_por_avaliacao_volta_na_lista_uma_vez(gama, lidas, usuario):
    # Duas avaliações na mesma refeição: um aviso e um item só (distinct).
    from django.contrib.auth import get_user_model

    outra = get_user_model().objects.create_user(
        matricula_siape="202400002",
        tipo_usuario="estudante",
        apelido="alana",
        email_institucional="202400002@aluno.unb.br",
        aceite_privacidade_em=usuario.aceite_privacidade_em,
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["jantar"])
    sexta = Refeicao.objects.get(campus=gama, data=DIAS[4], tipo="jantar")
    _criar_avaliacao(usuario, sexta)
    _criar_avaliacao(outra, sexta)
    gravadas = repositorio.salvar(
        gama, _fonte(gama), _sem_o_jantar_de_sexta(lidas["jantar"])
    )
    assert repositorio.remover_ausentes(gama, _fonte(gama), gravadas) == [sexta]


def test_cada_refeicao_apagada_fica_no_log(gama, lidas, caplog):
    # Revisão #218, item 9: as apagadas também deixam rastro.
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["jantar"])
    gravadas = repositorio.salvar(
        gama, _fonte(gama), _sem_o_jantar_de_sexta(lidas["jantar"])
    )
    with caplog.at_level(logging.INFO, logger="apps.cardapio.leitor"):
        assert repositorio.remover_ausentes(gama, _fonte(gama), gravadas) == []
    apagadas = [r.getMessage() for r in caplog.records if "apagada" in r.getMessage()]
    assert len(apagadas) == 1
    assert "2026-11-20" in apagadas[0] and "jantar" in apagadas[0]


def _uma_refeicao(data):
    return RefeicaoEstruturada(
        refeicao="almoco",
        dias=[{"dia": "", "data": data.isoformat()}],
        categorias=[],
    )


def test_limites_do_p1_sao_o_inicio_e_o_fim_do_link(gama):
    # Link de 16 a 22/11: as refeições de 16 e de 22 somem se não estão no
    # PDF relido; a de 23 (fim + 1) é de outra semana e fica.
    repositorio = CardapioRepository()
    for dia in (16, 22, 23):
        repositorio.salvar(gama, _fonte(gama), _uma_refeicao(date(2026, 11, dia)))
    gravadas = repositorio.salvar(gama, _fonte(gama), _uma_refeicao(date(2026, 11, 17)))
    repositorio.remover_ausentes(gama, _fonte(gama), gravadas)
    assert sorted(Refeicao.objects.values_list("data", flat=True)) == [
        date(2026, 11, 17),
        date(2026, 11, 23),
    ]


def test_remover_ausentes_so_mexe_na_semana_do_pdf_e_no_campus(gama, lidas):
    repositorio = CardapioRepository()
    repositorio.salvar(gama, _fonte(gama), lidas["almoco"])
    outra_semana = RefeicaoEstruturada(
        refeicao="almoco",
        dias=[{"dia": "2ª FEIRA", "data": "2026-11-23"}],
        categorias=[],
    )
    repositorio.salvar(gama, _fonte(gama), outra_semana)
    planaltina = Campus.objects.get(nome="Planaltina")
    repositorio.salvar(planaltina, _fonte(planaltina), lidas["almoco"])

    # Releitura da semana de 16/11 do Gama só com o almoço de segunda.
    so_segunda = RefeicaoEstruturada(
        refeicao="almoco",
        dias=[{"dia": "2ª FEIRA", "data": "2026-11-16"}],
        categorias=[],
    )
    gravadas = repositorio.salvar(gama, _fonte(gama), so_segunda)
    repositorio.remover_ausentes(gama, _fonte(gama), gravadas)

    assert sorted(
        Refeicao.objects.filter(campus=gama).values_list("data", flat=True)
    ) == [date(2026, 11, 16), date(2026, 11, 23)]
    assert Refeicao.objects.filter(campus=planaltina).count() == 5
