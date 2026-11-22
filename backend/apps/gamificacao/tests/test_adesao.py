"""PontuacaoRepository.alterar_adesao (BE-16, RF27.1, Gamificação N4 4c).

Liga e desliga `participa_ranking` e mais nada: não mexe nos pontos (nem é
desfeita por quem grava pontos) e não toca na `PontosSemestreCampus`, cujo
`atualizado_em` é o desempate do ranking.
"""

from datetime import UTC, date, datetime, time
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone

from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import em_brasilia
from apps.fila.models import Checkin
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from apps.gamificacao.pontuacao_repository import PontuacaoRepository
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    TipoContribuicao,
)

pytestmark = pytest.mark.django_db

TERCA = date(2026, 11, 24)
ANTES = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
DEPOIS = datetime(2026, 11, 22, 15, 0, tzinfo=UTC)


@pytest.fixture
def conta(db):
    conta = get_user_model().objects.create_user(
        matricula_siape="202400401",
        tipo_usuario="estudante",
        apelido="duda",
        email_institucional="202400401@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    PontuacaoService().inicializar_conta(conta)
    return conta


def alterar(conta, participa):
    PontuacaoRepository().alterar_adesao(conta, participa)


def participa(conta):
    return PontuacaoUsuario.objects.get(usuario=conta).participa_ranking


# --- 5.3 #1 a #4 -------------------------------------------------------------


def test_ligar_grava_true(conta):
    alterar(conta, True)

    assert participa(conta) is True


def test_ligar_e_depois_desligar_grava_false(conta):
    alterar(conta, True)
    alterar(conta, False)

    assert participa(conta) is False


def test_ligar_duas_vezes_e_idempotente(conta):
    alterar(conta, True)
    alterar(conta, True)

    assert participa(conta) is True


def test_desligar_sem_ter_ligado_e_idempotente(conta):
    alterar(conta, False)

    assert participa(conta) is False


@pytest.mark.parametrize("valor", [True, False])
def test_linha_faltando_e_criada_com_zero_ponto_e_o_valor_pedido(conta, valor):
    PontuacaoUsuario.objects.filter(usuario=conta).delete()

    alterar(conta, valor)

    pontuacao = PontuacaoUsuario.objects.get(usuario=conta)
    assert pontuacao.pontos_totais == 0
    assert pontuacao.participa_ranking is valor


# --- 5.3 #5: o desempate do ranking fica intacto -----------------------------


def test_adesao_nao_toca_na_linha_do_semestre(conta):
    campus = criar_campus()
    with mock.patch("django.utils.timezone.now", return_value=ANTES):
        linha = PontosSemestreCampus.objects.create(
            usuario=conta, campus=campus, semestre_referencia="2026.2", pontos=30
        )

    with mock.patch("django.utils.timezone.now", return_value=DEPOIS):
        alterar(conta, True)
        alterar(conta, False)

    linha_depois = PontosSemestreCampus.objects.get(pk=linha.pk)
    assert linha_depois.atualizado_em == linha.atualizado_em == ANTES
    assert linha_depois.pontos == 30


# --- 5.3 #6: adesão e pontos não se apagam -----------------------------------


def test_gravar_pontos_com_objeto_antigo_nao_desfaz_a_adesao(conta):
    repositorio = PontuacaoRepository()
    antiga = PontuacaoUsuario.objects.get(usuario=conta)

    repositorio.alterar_adesao(conta, True)
    antiga.pontos_totais += 10
    repositorio.salvar(antiga)

    pontuacao = PontuacaoUsuario.objects.get(usuario=conta)
    assert pontuacao.participa_ranking is True
    assert pontuacao.pontos_totais == 10


def test_adesao_nao_desfaz_pontos_gravados_depois_da_leitura(conta):
    """Os pontos mudam entre a leitura da adesão e a gravação dela (como uma
    gravação que só mexe em `pontos_totais`): a adesão grava só a coluna
    dela e os pontos ficam."""
    repositorio = PontuacaoRepository()
    travar_de_verdade = repositorio.travar_por_conta

    def travar_e_pontuar_por_fora(conta_travada):
        pontuacao = travar_de_verdade(conta_travada)
        PontuacaoUsuario.objects.filter(pk=pontuacao.pk).update(
            pontos_totais=F("pontos_totais") + 10
        )
        return pontuacao

    with mock.patch.object(
        repositorio, "travar_por_conta", side_effect=travar_e_pontuar_por_fora
    ):
        repositorio.alterar_adesao(conta, True)

    pontuacao = PontuacaoUsuario.objects.get(usuario=conta)
    assert pontuacao.participa_ranking is True
    assert pontuacao.pontos_totais == 10


# --- 5.3 #7: os pontos continuam com a adesão desligada (RF27.1) ------------


def test_checkin_com_adesao_desligada_continua_pontuando(conta):
    campus = criar_campus()
    alterar(conta, True)
    alterar(conta, False)
    checkin = Checkin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao=TipoRefeicao.ALMOCO,
        data=TERCA,
        registrado_em=em_brasilia(TERCA, time(12, 7)),
        faixa_inicio=time(12, 0),
    )

    PontuacaoService().registrar_contribuicao(
        conta,
        TipoContribuicao.CHECKIN,
        checkin.id,
        RefeicaoRef(campus=campus, tipo_refeicao=TipoRefeicao.ALMOCO, data=TERCA),
    )

    pontuacao = PontuacaoUsuario.objects.get(usuario=conta)
    assert pontuacao.participa_ranking is False
    assert pontuacao.pontos_totais == 10
    assert (
        PontosSemestreCampus.objects.get(
            usuario=conta, campus=campus, semestre_referencia="2026.2"
        ).pontos
        == 10
    )
