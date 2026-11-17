"""PontuacaoService (Gamificação N4): as versões mínimas da BE-05 e da BE-09.

A BE-14 expande o serviço sem mudar a assinatura de `inicializar_conta` nem a
de `registrar_contribuicao` (versão mínima da BE-09).
"""

from datetime import date

import pytest

from apps.cardapio.models import TipoRefeicao
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)


@pytest.mark.django_db
def test_inicializar_conta_cria_contadores_zerados(usuario):
    PontuacaoService().inicializar_conta(usuario)

    pontuacao = PontuacaoUsuario.objects.get(usuario=usuario)
    assert pontuacao.pontos_totais == 0
    assert pontuacao.sequencia_atual == 0
    assert pontuacao.ultima_semana_completada is None
    # Adesão ao ranking é opcional e começa desligada (RN12).
    assert pontuacao.participa_ranking is False


# --- registrar_contribuicao (versão mínima da BE-09) -------------------------


@pytest.mark.django_db
def test_registrar_contribuicao_ainda_nao_concede_pontos(usuario):
    """A BE-09 só liga o check-in à pontuação; a regra dos pontos é da BE-14."""
    PontuacaoService().inicializar_conta(usuario)
    refeicao = RefeicaoRef(
        campus=criar_campus(),
        tipo_refeicao=TipoRefeicao.ALMOCO,
        data=date(2026, 11, 17),
    )

    resultado = PontuacaoService().registrar_contribuicao(
        usuario, TipoContribuicao.CHECKIN, 1, refeicao
    )

    assert (resultado.total, resultado.contribuicao, resultado.avaliacao_liberada) == (
        0,
        0,
        0,
    )
    assert PontuacaoUsuario.objects.get(usuario=usuario).pontos_totais == 0


def test_total_soma_as_partes_do_resultado():
    assert ResultadoPontuacao(contribuicao=10, avaliacao_liberada=5).total == 15
