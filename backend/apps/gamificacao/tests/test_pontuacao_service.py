"""PontuacaoService.inicializar_conta (Gamificação N4, versão mínima da BE-05).

A BE-14 expande o serviço sem mudar a assinatura de `inicializar_conta`.
"""

import pytest

from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.pontuacao_service import PontuacaoService


@pytest.mark.django_db
def test_inicializar_conta_cria_contadores_zerados(usuario):
    PontuacaoService().inicializar_conta(usuario)

    pontuacao = PontuacaoUsuario.objects.get(usuario=usuario)
    assert pontuacao.pontos_totais == 0
    assert pontuacao.sequencia_atual == 0
    assert pontuacao.ultima_semana_completada is None
    # Adesão ao ranking é opcional e começa desligada (RN12).
    assert pontuacao.participa_ranking is False


@pytest.mark.django_db
def test_inicializar_conta_nao_devolve_nada(usuario):
    assert PontuacaoService().inicializar_conta(usuario) is None
