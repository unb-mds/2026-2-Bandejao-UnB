"""RankingService e PontuacaoRepository.elegiveis (BE-17, RF27.2, RN12,
Gamificação N4 4c).

O ranking é calculado na consulta: só quem aderiu, com conta ativa e ao
menos 1 ponto no semestre no campus, pelos pontos e com desempate por quem
pontuou antes (`atualizado_em` mais antigo), até o tamanho do ranking.
"""

from datetime import date

import pytest

from apps.cadastro.models import StatusUsuario
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.pontuacao_repository import PontuacaoRepository
from apps.gamificacao.ranking import LinhaRanking
from apps.gamificacao.ranking_service import RankingService
from apps.gamificacao.semestre_resolver import SemestreResolver
from apps.gamificacao.tests.apoio_ranking import SEMESTRE, criar_conta, pontuar
from config.parametros import ParametrosGamificacaoConfig

pytestmark = pytest.mark.django_db


# --- Apoio -------------------------------------------------------------------


def ids_do_top(campus, servico=None):
    servico = servico or RankingService()
    return [linha.conta.pk for linha in servico.top_publico(campus, SEMESTRE)]


@pytest.fixture
def campus(db):
    return criar_campus()


# --- Elegibilidade -----------------------------------------------------------


def test_quem_nao_aderiu_nao_aparece(campus):
    aderiu = criar_conta(1)
    nao_aderiu = criar_conta(2, aderiu=False)
    pontuar(aderiu, campus, 10)
    pontuar(nao_aderiu, campus, 500)

    assert ids_do_top(campus) == [aderiu.pk]


@pytest.mark.parametrize("status", [StatusUsuario.SUSPENSO, StatusUsuario.PENDENTE])
def test_conta_que_nao_esta_ativa_nao_aparece(campus, status):
    ativa = criar_conta(1)
    inativa = criar_conta(2, status=status)
    pontuar(ativa, campus, 10)
    pontuar(inativa, campus, 500)

    assert ids_do_top(campus) == [ativa.pk]


def test_quem_tem_zero_ponto_no_semestre_nao_aparece(campus):
    com_ponto = criar_conta(1)
    sem_ponto = criar_conta(2)
    pontuar(com_ponto, campus, 1)
    pontuar(sem_ponto, campus, 0)

    assert ids_do_top(campus) == [com_ponto.pk]


def test_pontos_de_outro_campus_e_de_outro_semestre_nao_entram(campus):
    outro_campus = criar_campus("Gama")
    conta = criar_conta(1)
    so_em_outro_campus = criar_conta(2)
    so_no_semestre_passado = criar_conta(3)
    pontuar(conta, campus, 10)
    pontuar(so_em_outro_campus, outro_campus, 500)
    pontuar(so_no_semestre_passado, campus, 500, semestre="2026.1")

    assert ids_do_top(campus) == [conta.pk]


def test_sem_elegiveis_a_lista_vem_vazia(campus):
    pontuar(criar_conta(1, aderiu=False), campus, 10)

    assert RankingService().top_publico(campus, SEMESTRE) == []


# --- Ordem, empate e tamanho -------------------------------------------------


def test_ordem_pelos_pontos_do_maior_para_o_menor(campus):
    contas = [criar_conta(n) for n in range(1, 4)]
    pontuar(contas[0], campus, 20)
    pontuar(contas[1], campus, 50)
    pontuar(contas[2], campus, 35)

    linhas = RankingService().top_publico(campus, SEMESTRE)

    assert linhas == [
        LinhaRanking(conta=contas[1], posicao=1, pontos=50),
        LinhaRanking(conta=contas[2], posicao=2, pontos=35),
        LinhaRanking(conta=contas[0], posicao=3, pontos=20),
    ]


def test_empate_vai_para_quem_pontuou_antes(campus):
    """O empatado criado depois pontuou antes: o desempate é pelo
    `atualizado_em`, não pela ordem de criação (id)."""
    pontuou_depois = criar_conta(1)
    pontuou_antes = criar_conta(2)
    pontuar(pontuou_depois, campus, 30, minutos=10)
    pontuar(pontuou_antes, campus, 30, minutos=5)

    linhas = RankingService().top_publico(campus, SEMESTRE)

    assert [(linha.conta.pk, linha.posicao) for linha in linhas] == [
        (pontuou_antes.pk, 1),
        (pontuou_depois.pk, 2),
    ]


def test_corta_no_tamanho_do_ranking(campus):
    tamanho = ParametrosGamificacaoConfig.tamanho_ranking
    contas = [criar_conta(n) for n in range(1, tamanho + 2)]
    for pontos, conta in enumerate(contas, start=1):
        pontuar(conta, campus, pontos)

    linhas = RankingService().top_publico(campus, SEMESTRE)

    assert len(linhas) == tamanho
    assert [linha.posicao for linha in linhas] == list(range(1, tamanho + 1))
    # Quem ficou de fora é o de menos pontos.
    assert contas[0].pk not in [linha.conta.pk for linha in linhas]


def test_tamanho_vem_do_construtor(campus):
    contas = [criar_conta(n) for n in range(1, 4)]
    for pontos, conta in enumerate(contas, start=1):
        pontuar(conta, campus, pontos)

    assert ids_do_top(campus, RankingService(tamanho=2)) == [
        contas[2].pk,
        contas[1].pk,
    ]


def test_linhas_trazem_a_pontuacao_da_conta_sem_consulta_extra(
    campus, django_assert_num_queries
):
    """A patente sai dos pontos totais (`conta.pontuacao`): a conta vem com a
    pontuação junto, numa consulta só para as 10 linhas, e o mapper não faz
    uma consulta por linha."""
    for n in range(1, 11):
        pontuar(criar_conta(n), campus, n)

    with django_assert_num_queries(2):
        linhas = RankingService().top_publico(campus, SEMESTRE)
        totais = [linha.conta.pontuacao.pontos_totais for linha in linhas]

    assert len(totais) == 10


# --- Repositório e semestre --------------------------------------------------


def test_elegiveis_traz_todos_os_elegiveis_em_ordem(campus):
    """Sem corte: a posição de quem está fora dos 10 vai servir ao "Meu
    progresso" depois da Release (RF33.3)."""
    contas = [criar_conta(n) for n in range(1, 13)]
    for pontos, conta in enumerate(contas, start=1):
        pontuar(conta, campus, pontos)

    linhas = PontuacaoRepository().elegiveis(campus, SEMESTRE)

    assert [linha.usuario_id for linha in linhas] == [
        conta.pk for conta in reversed(contas)
    ]


def test_semestre_corrente_vem_do_semestre_resolver():
    servico = RankingService(
        semestres=SemestreResolver(datas={"2026.2": date(2026, 12, 14)})
    )

    assert servico.semestre_corrente(date(2026, 11, 22)) == "2026.2"
    assert servico.semestre_corrente(date(2026, 12, 15)) == "2027.1"
