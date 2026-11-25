"""ProgressoService.montar (BE-16, RF26.1, RF26.2, Gamificação N4 4c).

Só leitura: a patente sai dos pontos totais, a adesão vem da
`PontuacaoUsuario`, e a conta sem a linha é tratada como zero ponto e sem
adesão, sem criar nada. Os campos de sequência ficam como a seção 4.5 do guia
decidiu até a BE-E6.
"""

from datetime import date, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import em_brasilia
from apps.fila.models import Checkin
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.patente import Patente
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    TipoContribuicao,
)
from apps.gamificacao.progresso import Progresso
from apps.gamificacao.progresso_service import ProgressoService
from config.parametros import ParametrosGamificacaoConfig

pytestmark = pytest.mark.django_db

TERCA = date(2026, 11, 24)


def criar_conta(numero, apelido):
    return get_user_model().objects.create_user(
        matricula_siape=f"2024002{numero:02d}",
        tipo_usuario="estudante",
        apelido=apelido,
        email_institucional=f"2024002{numero:02d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )


def com_pontuacao(conta, pontos=0, participa=False, sequencia=0):
    PontuacaoUsuario.objects.create(
        usuario=conta,
        pontos_totais=pontos,
        participa_ranking=participa,
        sequencia_atual=sequencia,
    )
    return conta


def montar(conta, hoje=TERCA):
    return ProgressoService().montar(conta, hoje)


@pytest.fixture
def conta(db):
    return criar_conta(1, "bia")


# --- 5.2 #1, #2 --------------------------------------------------------------


def test_conta_nova_e_caloura_sem_adesao(conta):
    PontuacaoService().inicializar_conta(conta)

    progresso = montar(conta)

    assert isinstance(progresso, Progresso)
    assert progresso.patente == Patente.CALOURO_DE_BANDEJA
    assert progresso.pontos_totais == 0
    assert progresso.falta_para_proxima == 150
    assert progresso.participa_ranking is False


def test_460_pontos_com_adesao_e_veterano(conta):
    com_pontuacao(conta, pontos=460, participa=True)

    progresso = montar(conta)

    assert progresso.patente == Patente.VETERANO
    assert progresso.pontos_totais == 460
    assert progresso.falta_para_proxima == 440
    assert progresso.participa_ranking is True


# --- 5.2 #3 ------------------------------------------------------------------


def test_sem_pontuacao_usuario_responde_zero_e_nao_cria_linha(conta):
    progresso = montar(conta)

    assert progresso.patente == Patente.CALOURO_DE_BANDEJA
    assert progresso.pontos_totais == 0
    assert progresso.falta_para_proxima == 150
    assert progresso.participa_ranking is False
    assert progresso.sequencia == 0
    assert not PontuacaoUsuario.objects.filter(usuario=conta).exists()


# --- 5.2 #4: não regride com o tempo (RF26.1) -------------------------------


def test_patente_nao_regride_com_o_tempo_sem_contribuicao(conta):
    com_pontuacao(conta, pontos=460)

    agora = montar(conta, hoje=TERCA)
    depois = montar(conta, hoje=TERCA + timedelta(weeks=10))

    assert depois.patente == agora.patente == Patente.VETERANO
    assert depois.pontos_totais == agora.pontos_totais == 460


# --- 5.2 #5: pontos reais atravessando o limiar ------------------------------


def test_checkin_que_atravessa_150_sobe_para_rato_de_ru(conta):
    com_pontuacao(conta, pontos=145)
    campus = criar_campus()
    antes = montar(conta)
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
    depois = montar(conta)

    assert antes.patente == Patente.CALOURO_DE_BANDEJA
    assert depois.patente == Patente.RATO_DE_RU
    assert depois.pontos_totais == 155
    assert depois.falta_para_proxima == 295


# --- 5.2 #6: campos de sequência (seção 4.5) ---------------------------------


def test_campos_de_sequencia_ate_a_be_e6(conta):
    com_pontuacao(conta, sequencia=4)

    progresso = montar(conta)

    assert progresso.sequencia == 4
    assert progresso.dias_na_semana == 0
    assert progresso.minimo_dias == ParametrosGamificacaoConfig.min_dias_semana


# --- 5.2 #7: cada um vê o próprio --------------------------------------------


def test_progresso_de_uma_conta_nao_muda_com_os_pontos_de_outra(conta):
    com_pontuacao(conta, pontos=10)
    outra = com_pontuacao(criar_conta(2, "caio"), pontos=1500, participa=True)

    antes = montar(conta)
    PontuacaoUsuario.objects.filter(usuario=outra).update(pontos_totais=5000)
    depois = montar(conta)

    assert antes == depois
    assert depois.pontos_totais == 10
    assert depois.patente == Patente.CALOURO_DE_BANDEJA
    assert depois.participa_ranking is False
    assert montar(outra).patente == Patente.LENDA_DO_RU
