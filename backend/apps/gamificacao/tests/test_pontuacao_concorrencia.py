"""Duas requisições simultâneas (BE-14, issue #166; Gamificação N4 4a, passo 1).

A trava por conta (`select_for_update` em `PontuacaoUsuario`) serializa as
contribuições da mesma conta, e o READ COMMITTED faz quem esperou a trava
enxergar o que a outra transação acabou de gravar.

O SQLite ignora `select_for_update` e trava o arquivo inteiro na escrita, então
estes testes só provam algo no MySQL: rodam no job `testes-mysql` do CI e,
localmente, contra o MySQL do `docker compose`.
"""

import threading
from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone

from apps.avaliacao.models import Avaliacao
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_refeicao
from apps.fila.models import Checkin
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    TipoContribuicao,
)

pytestmark = [
    pytest.mark.skipif(
        connection.vendor != "mysql",
        reason="o SQLite ignora select_for_update; roda no testes-mysql do CI",
    ),
    pytest.mark.django_db(transaction=True),
]

TERCA = date(2026, 11, 24)
ALMOCO = TipoRefeicao.ALMOCO
# Folga para a thread que espera a trava; no MySQL o padrão é 50 s.
TEMPO_MAXIMO_S = 30


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
def conta():
    conta = get_user_model().objects.create_user(
        matricula_siape="202400201",
        tipo_usuario="estudante",
        apelido="corrida",
        email_institucional="202400201@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
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


def test_mesmo_checkin_ao_mesmo_tempo_pontua_uma_vez(conta, darcy):
    checkin = novo_checkin(conta, darcy)

    def pontuar(barreira):
        barreira.wait()
        return PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.CHECKIN, checkin.id, refeicao_ref(darcy)
        )

    primeira, segunda = em_paralelo(pontuar, pontuar)

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


def test_duas_primeiras_contribuicoes_sem_linha_de_pontuacao(darcy):
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
