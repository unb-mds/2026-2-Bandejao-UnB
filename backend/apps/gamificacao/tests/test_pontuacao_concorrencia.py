"""Duas requisições simultâneas (BE-14, issue #166; Gamificação N4 4a, passo 1).

A trava por conta (`select_for_update` em `PontuacaoUsuario`) serializa as
contribuições da mesma conta, e o READ COMMITTED faz quem esperou a trava
enxergar o que a outra transação acabou de gravar.

O SQLite ignora `select_for_update` e trava o arquivo inteiro na escrita, então
estes testes só provam algo no MySQL: rodam no job `testes-mysql` do CI e,
localmente, contra um MySQL 8.4 (por exemplo, `docker run ... mysql:8.4`).

Uma barreira na entrada não garante que as transações se sobreponham: uma
thread pode terminar antes de a outra começar. Por isso a fixture
`sobrepor_no_servico` segura cada thread dentro do serviço, logo depois da
trava, e os testes de deadlock seguram cada uma logo depois da primeira trava
que ela pega.
"""

import threading
from datetime import date, time
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone

from apps.avaliacao.avaliacao_service import AvaliacaoService
from apps.avaliacao.models import Avaliacao
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_refeicao, em_brasilia
from apps.fila.checkin_service import CheckinService
from apps.fila.models import Checkin
from apps.fila.tests.apoio import RU_DARCY, ao_norte, criar_campus
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from apps.gamificacao.origem_contribuicao_repository import (
    OrigemContribuicaoRepository,
)
from apps.gamificacao.pontuacao_repository import PontuacaoRepository
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    TipoContribuicao,
)
from config.parametros import AvisoPrivacidadeConfig

pytestmark = [
    pytest.mark.skipif(
        connection.vendor != "mysql",
        reason="o SQLite ignora select_for_update; roda no testes-mysql do CI",
    ),
    pytest.mark.django_db(transaction=True),
]

TERCA = date(2026, 11, 24)
ALMOCO = TipoRefeicao.ALMOCO
DURANTE_O_ALMOCO = em_brasilia(TERCA, time(12, 7))
NO_RU = ao_norte(RU_DARCY, 20)
# Folga para a thread que espera a trava; no MySQL o padrão é 50 s.
TEMPO_MAXIMO_S = 30
# Quanto uma thread espera a outra dentro do serviço. Com a trava, a outra
# está parada na trava e não chega: a espera acaba sozinha nesse tempo.
JANELA_S = 2


def em_paralelo(*tarefas):
    """Roda cada tarefa numa thread, com conexão e transação próprias.

    Cada tarefa recebe uma `threading.Barrier` comum e a chama no ponto em
    que as duas devem estar juntas. Devolve os resultados na ordem das
    tarefas; um erro numa thread falha o teste.
    """
    barreira = threading.Barrier(len(tarefas), timeout=TEMPO_MAXIMO_S)
    resultados = [None] * len(tarefas)
    erros = []

    def rodar(indice, tarefa):
        try:
            with transaction.atomic():
                resultados[indice] = tarefa(barreira)
        except Exception as erro:  # noqa: BLE001 (a thread devolve o erro ao teste)
            erros.append(erro)
            barreira.abort()
        finally:
            connection.close()

    threads = [
        threading.Thread(target=rodar, args=(indice, tarefa))
        for indice, tarefa in enumerate(tarefas)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(TEMPO_MAXIMO_S)
    assert not any(thread.is_alive() for thread in threads), "thread travada"
    assert not erros, erros
    return resultados


@pytest.fixture
def sobrepor_no_servico():
    """Segura cada thread logo depois da trava, até a outra chegar (no máximo
    `JANELA_S`). Com a trava, a segunda está esperando a trava e não chega: a
    primeira segue sozinha. Sem a trava, as duas conferem o marcador juntas e
    o teste pega a pontuação em dobro."""
    barreira = threading.Barrier(2, timeout=JANELA_S)
    ja_pontuada = OrigemContribuicaoRepository.ja_pontuada

    def esperando_a_outra(repositorio, tipo, origem_id):
        try:
            barreira.wait()
        except threading.BrokenBarrierError:
            pass
        return ja_pontuada(repositorio, tipo, origem_id)

    with mock.patch.object(
        OrigemContribuicaoRepository,
        "ja_pontuada",
        autospec=True,
        side_effect=esperando_a_outra,
    ):
        yield


@pytest.fixture
def conta():
    conta = get_user_model().objects.create_user(
        matricula_siape="202400201",
        tipo_usuario="estudante",
        apelido="corrida",
        email_institucional="202400201@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita=AvisoPrivacidadeConfig.versao_atual,
        password="senha-forte-123",
    )
    PontuacaoService().inicializar_conta(conta)
    return conta


@pytest.fixture
def darcy():
    return criar_campus()


def novo_checkin(conta, campus):
    return Checkin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao=ALMOCO,
        data=TERCA,
        registrado_em=timezone.now(),
        faixa_inicio=time(12, 0),
    )


def refeicao_ref(campus):
    return RefeicaoRef(campus=campus, tipo_refeicao=ALMOCO, data=TERCA)


def test_mesmo_checkin_ao_mesmo_tempo_pontua_uma_vez(conta, darcy, sobrepor_no_servico):
    checkin = novo_checkin(conta, darcy)

    def pontuar(barreira):
        barreira.wait()
        return PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.CHECKIN, checkin.id, refeicao_ref(darcy)
        )

    primeira, segunda = em_paralelo(pontuar, pontuar)

    # É esta linha que pega a pontuação em dobro: sem a trava, as duas leem 0
    # e gravam 10, e o total sozinho não mostraria o erro.
    assert sorted((primeira.total, segunda.total)) == [0, 10]
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 10
    assert PontosSemestreCampus.objects.get(usuario=conta).pontos == 10


def test_checkin_e_avaliacao_da_mesma_refeicao_ao_mesmo_tempo_somam_15(conta, darcy):
    """O caso mais traiçoeiro: cada transação grava o seu registro, que a
    outra ainda não vê, e só depois chama a pontuação. Sem a trava + READ
    COMMITTED, as duas concluiriam "falta o outro" e o total ficaria 10."""
    refeicao = criar_refeicao(darcy, TERCA, ALMOCO)

    def fazer_checkin(barreira):
        checkin = novo_checkin(conta, darcy)
        barreira.wait()
        return PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.CHECKIN, checkin.id, refeicao_ref(darcy)
        )

    def avaliar(barreira):
        avaliacao = Avaliacao.objects.create(usuario=conta, refeicao=refeicao, nota=4)
        barreira.wait()
        return PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.AVALIACAO, avaliacao.id, refeicao_ref(darcy)
        )

    do_checkin, da_avaliacao = em_paralelo(fazer_checkin, avaliar)

    assert do_checkin.total + da_avaliacao.total == 15
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 15
    assert PontosSemestreCampus.objects.get(usuario=conta).pontos == 15
    assert Avaliacao.objects.get().pontos_concedidos_em is not None


def test_duas_primeiras_contribuicoes_sem_linha_de_pontuacao(
    darcy, sobrepor_no_servico
):
    """Linha faltando nas duas ao mesmo tempo: uma cria, a outra bate no
    UNIQUE e relê com trava, sem estragar a transação de quem chamou."""
    conta = get_user_model().objects.create_user(
        matricula_siape="202400202",
        tipo_usuario="estudante",
        apelido="sem-linha",
        email_institucional="202400202@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    checkin = novo_checkin(conta, darcy)

    def pontuar(barreira):
        barreira.wait()
        return PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.CHECKIN, checkin.id, refeicao_ref(darcy)
        )

    primeira, segunda = em_paralelo(pontuar, pontuar)

    assert sorted((primeira.total, segunda.total)) == [0, 10]
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 10


# --- Pelos services de verdade (revisão da BE-14) -----------------------------


def avaliar_pelo_servico(conta, refeicao, nota=4, comentario=None):
    return AvaliacaoService().avaliar(
        conta, refeicao, nota, comentario, DURANTE_O_ALMOCO
    )


def checkin_pelo_servico(conta, campus):
    return CheckinService().registrar(conta, campus, ALMOCO, NO_RU, DURANTE_O_ALMOCO)


def test_editar_a_avaliacao_e_fazer_checkin_ao_mesmo_tempo_nao_trava(conta, darcy):
    """O caso do deadlock: a avaliação foi feita antes do check-in, e a pessoa
    a edita enquanto faz o check-in. O check-in trava a conta e depois marca a
    avaliação; a edição não pode travar a avaliação antes da conta.

    Cada thread espera a outra logo depois da primeira trava da conta que
    pede (a edição, antes de pegá-la; o check-in, depois). Se a edição
    travasse a avaliação primeiro, as duas ficariam presas uma na outra e o
    InnoDB abortaria uma delas (erro 1213)."""
    almoco = criar_refeicao(darcy, TERCA, ALMOCO)
    assert avaliar_pelo_servico(conta, almoco, nota=2).pontos.total == 0
    papel = threading.local()
    travar_de_verdade = PontuacaoRepository.travar_por_conta

    def travar(repositorio, conta):
        primeira = not getattr(papel, "travou", False)
        papel.travou = True
        if primeira and papel.nome == "edicao":
            papel.barreira.wait()
        pontuacao = travar_de_verdade(repositorio, conta)
        if primeira and papel.nome == "checkin":
            papel.barreira.wait()
        return pontuacao

    def editar(barreira):
        papel.nome, papel.barreira = "edicao", barreira
        return avaliar_pelo_servico(conta, almoco, nota=5, comentario="Quente").pontos

    def fazer_checkin(barreira):
        papel.nome, papel.barreira = "checkin", barreira
        return checkin_pelo_servico(conta, darcy).pontos

    with mock.patch.object(
        PontuacaoRepository, "travar_por_conta", autospec=True, side_effect=travar
    ):
        da_edicao, do_checkin = em_paralelo(editar, fazer_checkin)

    assert (do_checkin.contribuicao, do_checkin.avaliacao_liberada) == (10, 5)
    assert da_edicao.total == 0
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 15
    avaliacao = Avaliacao.objects.get()
    assert (avaliacao.nota, avaliacao.comentario) == (5, "Quente")
    assert avaliacao.pontos_concedidos_em is not None


def test_duas_avaliacoes_ao_mesmo_tempo_depois_do_checkin_pontuam_uma_vez(conta, darcy):
    """Primeira avaliação e edição (ou duplo toque) juntas, com o check-in já
    feito: os 5 pontos saem uma vez só."""
    almoco = criar_refeicao(darcy, TERCA, ALMOCO)
    checkin_pelo_servico(conta, darcy)

    def avaliar(barreira):
        barreira.wait()
        return avaliar_pelo_servico(conta, almoco).pontos

    primeira, segunda = em_paralelo(avaliar, avaliar)

    assert sorted((primeira.total, segunda.total)) == [0, 5]
    assert Avaliacao.objects.count() == 1
    assert PontuacaoUsuario.objects.get(usuario=conta).pontos_totais == 15
