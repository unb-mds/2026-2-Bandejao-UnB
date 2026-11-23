"""RankingPublicoMapper (BE-17, RI10, RI12, ADR 0008): a única saída do
ranking para terceiros. Expõe posição, apelido e patente; nunca pontos.
Sem `distintivo` nesta Release (backlog, seção 3, item 6)."""

from dataclasses import fields
from types import SimpleNamespace

from apps.gamificacao.patente import Patente
from apps.gamificacao.patente_resolver import PatenteResolver
from apps.gamificacao.ranking import LinhaRanking, LinhaRankingPublica
from apps.gamificacao.ranking_publico_mapper import RankingPublicoMapper


def linha(pontos_totais, pontos_semestre=1, posicao=1, apelido="edu"):
    conta = SimpleNamespace(
        apelido=apelido, pontuacao=SimpleNamespace(pontos_totais=pontos_totais)
    )
    return LinhaRanking(conta=conta, posicao=posicao, pontos=pontos_semestre)


def test_para_publico_traz_posicao_apelido_e_patente():
    publica = RankingPublicoMapper().para_publico(
        linha(pontos_totais=460, posicao=3, apelido="maria")
    )

    assert publica == LinhaRankingPublica(
        posicao=3, apelido="maria", patente=Patente.VETERANO
    )


def test_patente_sai_dos_pontos_totais_e_nao_dos_do_semestre():
    """Os pontos do semestre ordenam o ranking; a patente é a do "Meu
    progresso", derivada dos pontos totais (RN11)."""
    publica = RankingPublicoMapper().para_publico(
        linha(pontos_totais=1500, pontos_semestre=10)
    )

    assert publica.patente == Patente.LENDA_DO_RU


def test_patente_usa_o_resolver_recebido():
    mapper = RankingPublicoMapper(patentes=PatenteResolver((0, 1, 2, 3, 4)))

    assert mapper.para_publico(linha(pontos_totais=2)).patente == Patente.VETERANO


def test_linha_publica_nao_tem_pontos_nem_distintivo():
    nomes = {campo.name for campo in fields(LinhaRankingPublica)}

    assert nomes == {"posicao", "apelido", "patente"}
