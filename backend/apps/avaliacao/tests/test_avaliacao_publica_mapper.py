"""AvaliacaoPublicaMapper: o autor só aparece pelo apelido (RI10, RNF07.4, N4 4b)."""

from dataclasses import fields

import pytest

from apps.avaliacao.avaliacao_publica_mapper import (
    USUARIO_REMOVIDO,
    AvaliacaoPublica,
    AvaliacaoPublicaMapper,
)
from apps.avaliacao.tests.apoio import avaliar

pytestmark = pytest.mark.django_db


def test_converte_com_o_apelido_do_autor(conta, almoco):
    avaliacao = avaliar(conta, almoco, nota=5, comentario="Feijão ótimo")

    [publica] = AvaliacaoPublicaMapper().para_publico([avaliacao])

    assert publica == AvaliacaoPublica(
        apelido="dani",
        nota=5,
        comentario="Feijão ótimo",
        criada_em=avaliacao.criada_em,
    )


def test_conta_apagada_aparece_como_usuario_removido(conta, almoco):
    """A exclusão de conta apaga a linha de USUARIO e o vínculo vira nulo
    (`SET_NULL`): a avaliação fica, o autor some (RNF07.4)."""
    avaliacao = avaliar(conta, almoco, nota=3)
    conta.delete()
    avaliacao.refresh_from_db()

    [publica] = AvaliacaoPublicaMapper().para_publico([avaliacao])

    assert USUARIO_REMOVIDO == "usuário removido"
    assert publica.apelido == USUARIO_REMOVIDO
    assert publica.nota == 3


def test_comentario_nulo_sai_como_texto_vazio(conta, almoco):
    avaliacao = avaliar(conta, almoco, comentario=None)

    [publica] = AvaliacaoPublicaMapper().para_publico([avaliacao])

    assert publica.comentario == ""


def test_mantem_a_ordem_recebida(conta, outra_conta, almoco):
    primeira = avaliar(conta, almoco)
    segunda = avaliar(outra_conta, almoco)

    publicas = AvaliacaoPublicaMapper().para_publico([segunda, primeira])

    assert [p.apelido for p in publicas] == ["rafa", "dani"]


def test_avaliacao_publica_so_tem_os_campos_do_contrato():
    """Campo novo aqui é decisão consciente (RI10, ADR 0008)."""
    assert [campo.name for campo in fields(AvaliacaoPublica)] == [
        "apelido",
        "nota",
        "comentario",
        "criada_em",
    ]
