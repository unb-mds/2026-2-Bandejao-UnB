"""PontuacaoService (Gamificação N4 4a): `inicializar_conta` (BE-05) e a regra
dos pontos de `registrar_contribuicao` (BE-14, RN09, Anexo A).

Os registros de origem (check-in, avaliação, pergunta de saída) são gravados
direto no banco, como a Fila e a Avaliação fazem antes de chamar o serviço.
A refeição de cada teste é o almoço de terça, 24/11/2026, semestre 2026.2.
"""

from datetime import UTC, date, datetime, time, timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from apps.avaliacao.models import Avaliacao
from apps.avaliacao.tests.apoio import avaliar
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_refeicao, em_brasilia
from apps.fila.models import Checkin, PerguntaSaida
from apps.fila.tests.apoio import RU_GAMA, criar_campus
from apps.gamificacao.erros import OrigemContribuicaoNaoEncontradaError
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from apps.gamificacao.origem_contribuicao_repository import (
    OrigemContribuicaoRepository,
)
from apps.gamificacao.pontuacao_policy import PontuacaoPolicy
from apps.gamificacao.pontuacao_repository import PontuacaoRepository
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)

TERCA = date(2026, 11, 24)
QUARTA = date(2026, 11, 25)
ALMOCO = TipoRefeicao.ALMOCO
JANTAR = TipoRefeicao.JANTAR
CHECKIN = TipoContribuicao.CHECKIN
AVALIACAO = TipoContribuicao.AVALIACAO


# --- Apoio -------------------------------------------------------------------


def criar_conta(numero, apelido):
    return get_user_model().objects.create_user(
        matricula_siape=f"2024001{numero:02d}",
        tipo_usuario="estudante",
        apelido=apelido,
        email_institucional=f"2024001{numero:02d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )


def fazer_checkin(conta, campus, data=TERCA, tipo=ALMOCO):
    """Check-in confirmado, gravado como o `CheckinService` grava."""
    return Checkin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao=tipo,
        data=data,
        registrado_em=em_brasilia(data, time(12, 7)),
        faixa_inicio=time(12, 0),
    )


def ref(campus, data=TERCA, tipo=ALMOCO):
    return RefeicaoRef(campus=campus, tipo_refeicao=tipo, data=data)


def pontuar_checkin(conta, checkin):
    return PontuacaoService().registrar_contribuicao(
        conta,
        CHECKIN,
        checkin.id,
        ref(checkin.campus, checkin.data, checkin.tipo_refeicao),
    )


def pontuar_avaliacao(conta, avaliacao):
    refeicao = avaliacao.refeicao
    return PontuacaoService().registrar_contribuicao(
        conta,
        AVALIACAO,
        avaliacao.id,
        ref(refeicao.campus, refeicao.data, refeicao.tipo),
    )


def partes(resultado):
    return (resultado.contribuicao, resultado.avaliacao_liberada, resultado.total)


def pontos_totais(conta):
    return PontuacaoUsuario.objects.get(usuario=conta).pontos_totais


def pontos_semestre(conta, campus, semestre="2026.2"):
    return PontosSemestreCampus.objects.get(
        usuario=conta, campus=campus, semestre_referencia=semestre
    ).pontos


def recarregar(registro):
    registro.refresh_from_db()
    return registro


@pytest.fixture
def conta(db):
    conta = criar_conta(1, "dani")
    PontuacaoService().inicializar_conta(conta)
    return conta


@pytest.fixture
def outra_conta(db):
    conta = criar_conta(2, "rafa")
    PontuacaoService().inicializar_conta(conta)
    return conta


@pytest.fixture
def darcy(db):
    return criar_campus()


@pytest.fixture
def gama(db):
    return criar_campus(nome="Gama", ru=RU_GAMA)


@pytest.fixture
def almoco(darcy):
    return criar_refeicao(darcy, TERCA, ALMOCO)


# --- inicializar_conta (BE-05) -----------------------------------------------


@pytest.mark.django_db
def test_inicializar_conta_cria_contadores_zerados(usuario):
    PontuacaoService().inicializar_conta(usuario)

    pontuacao = PontuacaoUsuario.objects.get(usuario=usuario)
    assert pontuacao.pontos_totais == 0
    assert pontuacao.sequencia_atual == 0
    assert pontuacao.ultima_semana_completada is None
    # Adesão ao ranking é opcional e começa desligada (RN12).
    assert pontuacao.participa_ranking is False


def test_total_soma_as_partes_do_resultado():
    assert ResultadoPontuacao(contribuicao=10, avaliacao_liberada=5).total == 15


# --- 1, 2: check-in ----------------------------------------------------------


def test_checkin_confirmado_concede_10_pontos_e_marca(conta, darcy):
    checkin = fazer_checkin(conta, darcy)

    resultado = pontuar_checkin(conta, checkin)

    assert partes(resultado) == (10, 0, 10)
    assert pontos_totais(conta) == 10
    assert pontos_semestre(conta, darcy) == 10
    assert recarregar(checkin).pontos_concedidos_em is not None


def test_mesmo_checkin_pontuado_duas_vezes_so_pontua_uma(conta, darcy):
    checkin = fazer_checkin(conta, darcy)
    pontuar_checkin(conta, checkin)

    resultado = pontuar_checkin(conta, checkin)

    assert partes(resultado) == (0, 0, 0)
    assert pontos_totais(conta) == 10
    assert pontos_semestre(conta, darcy) == 10


def test_marcador_vem_do_banco_e_nao_do_objeto_de_quem_chama(conta, darcy):
    """Item 3 da seção 4.2: o objeto antigo não tem o marcador, o banco tem."""
    checkin = fazer_checkin(conta, darcy)
    Checkin.objects.filter(id=checkin.id).update(pontos_concedidos_em=timezone.now())

    resultado = pontuar_checkin(conta, checkin)

    assert resultado.total == 0
    assert pontos_totais(conta) == 0


# --- 3 a 9: avaliação (RN09) -------------------------------------------------


def test_avaliacao_com_checkin_na_mesma_refeicao_concede_5(conta, darcy, almoco):
    fazer_checkin(conta, darcy)
    avaliacao = avaliar(conta, almoco)

    resultado = pontuar_avaliacao(conta, avaliacao)

    assert partes(resultado) == (5, 0, 5)
    assert recarregar(avaliacao).pontos_concedidos_em is not None


def test_avaliacao_sem_checkin_nao_pontua_nem_marca(conta, almoco):
    avaliacao = avaliar(conta, almoco)

    resultado = pontuar_avaliacao(conta, avaliacao)

    assert partes(resultado) == (0, 0, 0)
    assert pontos_totais(conta) == 0
    assert recarregar(avaliacao).pontos_concedidos_em is None
    # Ninguém ganhou ponto: a linha do ranking não é criada (desempate).
    assert not PontosSemestreCampus.objects.exists()


def test_avaliacao_antes_e_checkin_depois_libera_a_avaliacao(conta, darcy, almoco):
    avaliacao = avaliar(conta, almoco)
    assert pontuar_avaliacao(conta, avaliacao).total == 0

    resultado = pontuar_checkin(conta, fazer_checkin(conta, darcy))

    assert partes(resultado) == (10, 5, 15)
    assert pontos_totais(conta) == 15
    assert pontos_semestre(conta, darcy) == 15
    assert recarregar(avaliacao).pontos_concedidos_em is not None


def test_avaliacao_editada_nao_pontua_de_novo(conta, darcy, almoco):
    fazer_checkin(conta, darcy)
    avaliacao = avaliar(conta, almoco)
    pontuar_avaliacao(conta, avaliacao)

    # A edição chama o serviço de novo com o mesmo `origem_id`.
    resultado = pontuar_avaliacao(conta, avaliacao)

    assert resultado.total == 0
    assert pontos_totais(conta) == 5


def test_avaliacao_liberada_no_checkin_e_depois_editada_nao_pontua(
    conta, darcy, almoco
):
    avaliacao = avaliar(conta, almoco)
    pontuar_avaliacao(conta, avaliacao)
    pontuar_checkin(conta, fazer_checkin(conta, darcy))

    resultado = pontuar_avaliacao(conta, avaliacao)

    assert resultado.total == 0
    assert pontos_totais(conta) == 15


def test_avaliacao_em_outro_campus_nao_pontua_nem_e_liberada(conta, darcy, gama):
    """Mesmo tipo e data, campus diferente: não é a mesma refeição."""
    avaliacao = avaliar(conta, criar_refeicao(gama, TERCA, ALMOCO))
    checkin = fazer_checkin(conta, darcy)

    assert pontuar_avaliacao(conta, avaliacao).total == 0
    assert recarregar(avaliacao).pontos_concedidos_em is None

    resultado = pontuar_checkin(conta, checkin)

    assert partes(resultado) == (10, 0, 10)
    assert recarregar(avaliacao).pontos_concedidos_em is None


@pytest.mark.parametrize(
    ("data", "tipo"),
    [(TERCA, JANTAR), (QUARTA, ALMOCO)],
    ids=["outro-tipo", "outra-data"],
)
def test_avaliacao_de_outra_refeicao_nao_pontua(conta, darcy, data, tipo):
    fazer_checkin(conta, darcy)
    avaliacao = avaliar(conta, criar_refeicao(darcy, data, tipo))

    resultado = pontuar_avaliacao(conta, avaliacao)

    assert resultado.total == 0
    assert recarregar(avaliacao).pontos_concedidos_em is None


@pytest.mark.parametrize(
    ("data", "tipo"),
    [(TERCA, JANTAR), (QUARTA, ALMOCO)],
    ids=["outro-tipo", "outra-data"],
)
def test_checkin_nao_libera_avaliacao_de_outra_refeicao(conta, darcy, data, tipo):
    avaliacao = avaliar(conta, criar_refeicao(darcy, data, tipo))

    resultado = pontuar_checkin(conta, fazer_checkin(conta, darcy))

    assert resultado.avaliacao_liberada == 0
    assert recarregar(avaliacao).pontos_concedidos_em is None


# --- 10, 11: pontos do semestre no campus da refeição ------------------------


def test_pontos_vao_para_o_campus_da_refeicao(conta, darcy, gama):
    pontuar_checkin(conta, fazer_checkin(conta, gama))

    assert pontos_semestre(conta, gama) == 10
    assert not PontosSemestreCampus.objects.filter(campus=darcy).exists()


def test_duas_contribuicoes_no_mesmo_semestre_e_campus_somam_numa_linha(conta, darcy):
    pontuar_checkin(conta, fazer_checkin(conta, darcy, tipo=ALMOCO))
    pontuar_checkin(conta, fazer_checkin(conta, darcy, tipo=JANTAR))

    assert PontosSemestreCampus.objects.filter(usuario=conta).count() == 1
    assert pontos_semestre(conta, darcy) == 20
    assert pontos_totais(conta) == 20


def test_atualizado_em_muda_quando_ganha_ponto(conta, darcy):
    """Desempate do ranking: `.update()` não dispara `auto_now` (seção 4.2)."""
    pontuar_checkin(conta, fazer_checkin(conta, darcy, tipo=ALMOCO))
    linha = PontosSemestreCampus.objects.get()
    antes = timezone.now() - timedelta(days=1)
    PontosSemestreCampus.objects.update(atualizado_em=antes)
    PontuacaoUsuario.objects.update(atualizado_em=antes)

    pontuar_checkin(conta, fazer_checkin(conta, darcy, tipo=JANTAR))

    assert recarregar(linha).atualizado_em > antes
    assert PontuacaoUsuario.objects.get(usuario=conta).atualizado_em > antes


def test_contribuicao_sem_ponto_nao_grava_a_linha_do_semestre(conta, darcy, almoco):
    """Item 5 da seção 4.2: só grava a linha quando a pessoa ganha ponto."""
    pontuar_checkin(conta, fazer_checkin(conta, darcy))
    antes = timezone.now() - timedelta(days=1)
    PontosSemestreCampus.objects.update(atualizado_em=antes)
    PontuacaoUsuario.objects.update(atualizado_em=antes)
    checkin = Checkin.objects.get()

    pontuar_checkin(conta, checkin)
    pontuar_avaliacao(conta, avaliar(conta, criar_refeicao(darcy, QUARTA, ALMOCO)))

    assert PontosSemestreCampus.objects.get().atualizado_em == antes
    assert PontuacaoUsuario.objects.get(usuario=conta).atualizado_em == antes


def test_checkin_nas_ferias_vai_para_o_semestre_seguinte(conta, darcy):
    """Config real: 2026.2 termina em 14/12/2026 (seção 4.4)."""
    ferias = date(2026, 12, 15)

    pontuar_checkin(conta, fazer_checkin(conta, darcy, data=ferias))

    assert pontos_semestre(conta, darcy, "2027.1") == 10
    assert not PontosSemestreCampus.objects.filter(
        semestre_referencia="2026.2"
    ).exists()


def test_ultimo_dia_do_semestre_ainda_conta_para_ele(conta, darcy):
    pontuar_checkin(conta, fazer_checkin(conta, darcy, data=date(2026, 12, 14)))

    assert pontos_semestre(conta, darcy, "2026.2") == 10


# --- 12: linha de pontuação faltando -----------------------------------------


@pytest.mark.django_db
def test_pontuacao_usuario_faltando_e_criada_com_os_pontos(darcy):
    conta = criar_conta(3, "sem-linha")
    assert not PontuacaoUsuario.objects.filter(usuario=conta).exists()

    resultado = pontuar_checkin(conta, fazer_checkin(conta, darcy))

    assert resultado.total == 10
    assert pontos_totais(conta) == 10


@pytest.mark.django_db
def test_linha_criada_por_outra_requisicao_e_relida_com_trava():
    """A outra requisição criou a linha entre a leitura e a criação: o UNIQUE
    desfaz só o savepoint, e a transação de quem chamou continua usável."""
    conta = criar_conta(4, "corrida")
    PontuacaoUsuario.objects.create(usuario=conta, pontos_totais=7)
    ler_de_verdade = PontuacaoRepository._ler_com_trava
    leituras = []

    def ler(conta):
        leituras.append(conta)
        # Na primeira leitura a linha da outra requisição ainda não aparecia.
        return None if len(leituras) == 1 else ler_de_verdade(conta)

    with mock.patch.object(PontuacaoRepository, "_ler_com_trava", side_effect=ler):
        pontuacao = PontuacaoRepository().travar_por_conta(conta)

    assert pontuacao.pontos_totais == 7
    assert len(leituras) == 2
    assert PontuacaoUsuario.objects.filter(usuario=conta).count() == 1


@pytest.mark.django_db
def test_integrity_error_que_nao_e_o_unique_sobe():
    conta = criar_conta(5, "erro")

    with (
        mock.patch.object(PontuacaoRepository, "_ler_com_trava", return_value=None),
        mock.patch.object(
            PontuacaoUsuario.objects, "create", side_effect=IntegrityError("outro")
        ),
        pytest.raises(IntegrityError),
    ):
        PontuacaoRepository().travar_por_conta(conta)


# --- 13, 14: política e pergunta de saída ------------------------------------


@pytest.mark.parametrize(
    ("tipo", "pontos"),
    [
        (TipoContribuicao.CHECKIN, 10),
        (TipoContribuicao.AVALIACAO, 5),
        (TipoContribuicao.RESPOSTA_SAIDA, 15),
    ],
)
def test_politica_so_depende_do_tipo(tipo, pontos):
    assert PontuacaoPolicy().pontos_por(tipo) == pontos


@pytest.mark.parametrize("tipo", list(TipoContribuicao))
def test_politica_cobre_todo_tipo_de_contribuicao(tipo):
    """Um tipo novo esquecido na política falha aqui, e não com `KeyError` em
    produção."""
    assert PontuacaoPolicy().pontos_por(tipo) > 0


def test_resposta_saida_concede_15_e_marca_a_pergunta_uma_vez(conta, darcy, almoco):
    checkin = fazer_checkin(conta, darcy)
    avaliacao = avaliar(conta, almoco)
    agora = timezone.now()
    pergunta = PerguntaSaida.objects.create(
        checkin=checkin,
        devida_em=agora + timedelta(minutes=15),
        expira_em=agora + timedelta(minutes=60),
    )

    def responder():
        return PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.RESPOSTA_SAIDA, pergunta.id, ref(darcy)
        )

    assert partes(responder()) == (15, 0, 15)
    assert recarregar(pergunta).pontos_concedidos_em is not None
    assert responder().total == 0
    assert pontos_totais(conta) == 15
    # A pergunta não libera a avaliação feita antes: só o check-in libera
    # (RN09). Nem o check-in dela é marcado.
    assert recarregar(avaliacao).pontos_concedidos_em is None
    assert recarregar(checkin).pontos_concedidos_em is None


# --- Origem que não existe (revisão da BE-14) --------------------------------


def test_marcar_pontuada_diz_se_marcou(conta, darcy):
    origens = OrigemContribuicaoRepository()
    checkin = fazer_checkin(conta, darcy)
    agora = timezone.now()

    assert origens.marcar_pontuada(CHECKIN, checkin.id, agora) is True
    assert origens.marcar_pontuada(CHECKIN, checkin.id, agora) is False
    assert origens.marcar_pontuada(CHECKIN, checkin.id + 1000, agora) is False


@pytest.mark.parametrize(
    "tipo",
    [CHECKIN, AVALIACAO, TipoContribuicao.RESPOSTA_SAIDA],
)
def test_origem_que_nao_existe_nao_pontua_e_desfaz(conta, darcy, tipo):
    """Um `origem_id` que não existe (ou de outro tipo) não pode pontuar: sem o
    marcador gravado, cada nova chamada pontuaria de novo. O erro desfaz a
    transação de quem chamou."""
    checkin = fazer_checkin(conta, darcy)
    inexistente = checkin.id + 1000

    with pytest.raises(OrigemContribuicaoNaoEncontradaError):
        PontuacaoService().registrar_contribuicao(conta, tipo, inexistente, ref(darcy))

    assert pontos_totais(conta) == 0
    assert not PontosSemestreCampus.objects.exists()


def test_id_de_checkin_como_resposta_de_saida_nao_pontua(conta, darcy):
    """O id existe, mas é de um `Checkin`, não de uma `PerguntaSaida`."""
    checkin = fazer_checkin(conta, darcy)

    with pytest.raises(OrigemContribuicaoNaoEncontradaError):
        PontuacaoService().registrar_contribuicao(
            conta, TipoContribuicao.RESPOSTA_SAIDA, checkin.id, ref(darcy)
        )

    assert pontos_totais(conta) == 0
    assert recarregar(checkin).pontos_concedidos_em is None


# --- 15: conta de outra pessoa -----------------------------------------------


def test_checkin_de_outra_conta_nao_libera_avaliacao(conta, outra_conta, darcy, almoco):
    avaliacao = avaliar(conta, almoco)

    resultado = pontuar_checkin(outra_conta, fazer_checkin(outra_conta, darcy))

    assert partes(resultado) == (10, 0, 10)
    assert recarregar(avaliacao).pontos_concedidos_em is None
    assert pontos_totais(conta) == 0


def test_checkin_de_outra_conta_nao_conta_para_a_avaliacao(
    conta, outra_conta, darcy, almoco
):
    fazer_checkin(outra_conta, darcy)

    assert pontuar_avaliacao(conta, avaliar(conta, almoco)).total == 0


# --- 16 a 18: avaliação ocultada pela moderação (ADR 0004) -------------------


def test_avaliacao_oculta_com_checkin_nao_pontua(conta, darcy, almoco):
    fazer_checkin(conta, darcy)
    avaliacao = avaliar(conta, almoco, oculta=True)

    resultado = pontuar_avaliacao(conta, avaliacao)

    assert resultado.total == 0
    assert recarregar(avaliacao).pontos_concedidos_em is None
    assert pontos_totais(conta) == 0


def test_checkin_nao_libera_avaliacao_oculta(conta, darcy, almoco):
    avaliacao = avaliar(conta, almoco, oculta=True)
    pontuar_avaliacao(conta, avaliacao)

    resultado = pontuar_checkin(conta, fazer_checkin(conta, darcy))

    assert partes(resultado) == (10, 0, 10)
    assert recarregar(avaliacao).pontos_concedidos_em is None


def test_avaliacao_pontuada_e_depois_ocultada_mantem_os_pontos(conta, darcy, almoco):
    fazer_checkin(conta, darcy)
    avaliacao = avaliar(conta, almoco)
    pontuar_avaliacao(conta, avaliacao)

    Avaliacao.objects.filter(id=avaliacao.id).update(oculta=True)
    # A edição de uma avaliação oculta chama o serviço de novo.
    resultado = pontuar_avaliacao(conta, avaliacao)

    assert resultado.total == 0
    assert pontos_totais(conta) == 5
    assert pontos_semestre(conta, darcy) == 5


# --- Marcador gravado com a hora da contribuição -----------------------------


def test_marcador_e_a_hora_da_contribuicao(conta, darcy, almoco, monkeypatch):
    agora = datetime(2026, 11, 24, 15, 7, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: agora)
    avaliacao = avaliar(conta, almoco)
    checkin = fazer_checkin(conta, darcy)

    pontuar_checkin(conta, checkin)

    assert recarregar(checkin).pontos_concedidos_em == agora
    assert recarregar(avaliacao).pontos_concedidos_em == agora
