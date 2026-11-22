"""Validadores da avaliação: janela, nota e comentário (RF15.1, Avaliação N4 4a)."""

from datetime import UTC, datetime, time, timedelta

import pytest

from apps.avaliacao.comentario_validator import ComentarioValidator
from apps.avaliacao.erros import ComentarioMuitoLongoError, NotaInvalidaError
from apps.avaliacao.janela_avaliacao_validator import JanelaAvaliacaoValidator
from apps.avaliacao.nota_validator import NotaValidator
from apps.avaliacao.tests.apoio import QUARTA, SEGUNDA, TERCA
from apps.cardapio.models import Refeicao, TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import em_brasilia

# --- JanelaAvaliacaoValidator ------------------------------------------------


def refeicao(dia=TERCA, tipo=TipoRefeicao.ALMOCO):
    # Sem banco: o validador só lê `data` e `tipo`.
    return Refeicao(data=dia, tipo=tipo)


@pytest.mark.parametrize(
    ("tipo", "inicio"),
    [
        (TipoRefeicao.CAFE, time(7, 0)),
        (TipoRefeicao.ALMOCO, time(11, 0)),
        (TipoRefeicao.JANTAR, time(17, 0)),
    ],
)
def test_abre_no_minuto_de_inicio_do_anexo_a(tipo, inicio):
    janela = JanelaAvaliacaoValidator()
    um_segundo_antes = em_brasilia(TERCA, inicio) - timedelta(seconds=1)

    assert janela.pode_avaliar(refeicao(tipo=tipo), em_brasilia(TERCA, inicio))
    assert not janela.pode_avaliar(refeicao(tipo=tipo), um_segundo_antes)


def test_continua_aberta_depois_do_fim_da_refeicao_ate_23h59():
    janela = JanelaAvaliacaoValidator()

    assert janela.pode_avaliar(refeicao(), em_brasilia(TERCA, time(14, 31)))
    assert janela.pode_avaliar(refeicao(), em_brasilia(TERCA, time(23, 59, 59)))


def test_fecha_a_meia_noite():
    assert not JanelaAvaliacaoValidator().pode_avaliar(
        refeicao(), em_brasilia(QUARTA, time(0, 0))
    )


def test_refeicao_de_outro_dia_nao_pode_ser_avaliada():
    janela = JanelaAvaliacaoValidator()
    meio_dia_de_terca = em_brasilia(TERCA, time(12, 0))

    assert not janela.pode_avaliar(refeicao(dia=SEGUNDA), meio_dia_de_terca)
    assert not janela.pode_avaliar(refeicao(dia=QUARTA), meio_dia_de_terca)


def test_dia_e_hora_sao_os_de_brasilia():
    """1h de quarta em UTC ainda é 22h de terça em Brasília."""
    agora_utc = datetime(2026, 11, 25, 1, 0, tzinfo=UTC)

    assert JanelaAvaliacaoValidator().pode_avaliar(refeicao(), agora_utc)
    assert not JanelaAvaliacaoValidator().pode_avaliar(refeicao(dia=QUARTA), agora_utc)


def test_inicio_vem_do_anexo_a_e_nao_da_copia_na_refeicao():
    """A refeição guarda o horário da época da leitura; vale o Anexo A atual."""
    antiga = refeicao()
    antiga.horario_inicio = time(10, 0)

    assert not JanelaAvaliacaoValidator().pode_avaliar(
        antiga, em_brasilia(TERCA, time(10, 30))
    )


# --- NotaValidator -----------------------------------------------------------


@pytest.mark.parametrize("nota", [1, 2, 3, 4, 5])
def test_nota_de_1_a_5_e_valida(nota):
    NotaValidator().validar(nota)


@pytest.mark.parametrize(
    "nota", [None, 0, 6, -1, 4.0, 4.5, "4", True, False, [4], {"nota": 4}]
)
def test_nota_ausente_fora_da_faixa_ou_que_nao_e_inteiro_e_invalida(nota):
    with pytest.raises(NotaInvalidaError):
        NotaValidator().validar(nota)


# --- ComentarioValidator -----------------------------------------------------


def test_comentario_ausente_ou_em_branco_vira_none():
    validador = ComentarioValidator()

    assert validador.validar(None) is None
    assert validador.validar("") is None
    assert validador.validar("   \n ") is None


@pytest.mark.parametrize(
    "texto",
    [
        "\u200b",  # espaço de largura zero
        "\u200b \u200b",
        "\ufeff",  # BOM
        "\u2060",  # word joiner
        "\u200d",  # zero width joiner
        "\u00a0\u200b",
        "\u3164",  # Hangul filler, que renderiza como espaço
        "\u115f\u1160",
        "\uffa0",
    ],
)
def test_comentario_so_com_caracteres_invisiveis_vira_none(texto):
    """Senão aparece um comentário em branco para todo mundo (revisão do #230)."""
    assert ComentarioValidator().validar(texto) is None


def test_caractere_invisivel_dentro_do_texto_fica():
    """O ZWJ junta emojis: só o comentário inteiro invisível vira None."""
    texto = "Cozinheira 👩\u200d🍳 caprichou"

    assert ComentarioValidator().validar(texto) == texto


def test_comentario_sai_sem_os_espacos_das_pontas():
    assert ComentarioValidator().validar("  feijão salgado \n") == "feijão salgado"


def test_comentario_com_500_caracteres_e_aceito():
    texto = "a" * ComentarioValidator.MAX_CARACTERES

    assert ComentarioValidator().validar(texto) == texto
    assert ComentarioValidator.MAX_CARACTERES == 500


def test_comentario_com_501_caracteres_e_recusado():
    with pytest.raises(ComentarioMuitoLongoError):
        ComentarioValidator().validar("a" * 501)


def test_limite_conta_caracteres_e_nao_bytes():
    """ "ç" e emoji ocupam mais de um byte, mas contam como um caractere."""
    texto = "ç" * 250 + "🍛" * 250

    assert ComentarioValidator().validar(texto) == texto


def test_espacos_das_pontas_nao_contam_no_limite():
    texto = "a" * 500

    assert ComentarioValidator().validar(f"  {texto}  ") == texto
