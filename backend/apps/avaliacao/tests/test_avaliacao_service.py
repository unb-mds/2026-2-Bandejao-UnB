"""AvaliacaoService: upsert com pontuação na mesma transação (RF15.1, Avaliação N4 4a)."""

from datetime import time, timedelta
from unittest import mock

import pytest
from django.db import IntegrityError

from apps.avaliacao.avaliacao_repository import AvaliacaoRepository
from apps.avaliacao.avaliacao_service import AvaliacaoService
from apps.avaliacao.erros import (
    AvaliacaoIndisponivelError,
    ComentarioMuitoLongoError,
    NotaInvalidaError,
)
from apps.avaliacao.models import Avaliacao
from apps.avaliacao.tests.apoio import DURANTE_O_ALMOCO, SEGUNDA, TERCA, avaliar
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_campus, criar_refeicao, em_brasilia
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)

pytestmark = pytest.mark.django_db


def registrar(conta, refeicao, nota=4, comentario=None, agora=DURANTE_O_ALMOCO):
    return AvaliacaoService().avaliar(conta, refeicao, nota, comentario, agora)


# --- criar -------------------------------------------------------------------


def test_primeira_avaliacao_e_gravada_ligada_a_conta(conta, almoco):
    registrada = registrar(conta, almoco, nota=5, comentario="Arroz soltinho")

    avaliacao = Avaliacao.objects.get()
    assert registrada.avaliacao == avaliacao
    assert registrada.criada is True
    assert (avaliacao.usuario, avaliacao.refeicao) == (conta, almoco)
    assert (avaliacao.nota, avaliacao.comentario) == (5, "Arroz soltinho")
    assert avaliacao.editada_em is None
    assert avaliacao.oculta is False


def test_comentario_em_branco_e_gravado_como_nulo(conta, almoco):
    registrar(conta, almoco, comentario="   ")

    assert Avaliacao.objects.get().comentario is None


# --- editar (upsert) ---------------------------------------------------------


def test_avaliar_de_novo_edita_a_anterior_sem_duplicar(conta, almoco):
    primeira = registrar(conta, almoco, nota=2, comentario="Frio")
    depois = DURANTE_O_ALMOCO + timedelta(hours=3)

    segunda = registrar(conta, almoco, nota=4, comentario=None, agora=depois)

    avaliacao = Avaliacao.objects.get()
    assert segunda.criada is False
    assert segunda.avaliacao.id == primeira.avaliacao.id
    assert (avaliacao.nota, avaliacao.comentario) == (4, None)
    assert avaliacao.editada_em == depois
    assert avaliacao.criada_em == primeira.avaliacao.criada_em


def test_edicao_nao_mexe_no_marcador_de_pontos_nem_na_ocultacao(conta, almoco):
    """O marcador é da Gamificação e a ocultação é da equipe (ADR 0011, ADR 0004).

    Gravar a avaliação inteira de volta apagaria um marcador escrito entre a
    leitura e a gravação, e os pontos sairiam em dobro.
    """
    existente = avaliar(conta, almoco, nota=2)
    concedidos_em = em_brasilia(TERCA, time(12, 0))
    buscar = AvaliacaoRepository.buscar_por_conta_e_refeicao

    def outra_escrita_depois_da_leitura(self, *args, **kwargs):
        lida = buscar(self, *args, **kwargs)
        Avaliacao.objects.filter(pk=existente.pk).update(
            pontos_concedidos_em=concedidos_em, oculta=True
        )
        return lida

    with mock.patch.object(
        AvaliacaoRepository,
        "buscar_por_conta_e_refeicao",
        outra_escrita_depois_da_leitura,
    ):
        registrar(conta, almoco, nota=5)

    existente.refresh_from_db()
    assert existente.nota == 5
    assert existente.pontos_concedidos_em == concedidos_em
    assert existente.oculta is True


def test_cada_conta_tem_a_sua_avaliacao_da_refeicao(conta, outra_conta, almoco):
    registrar(conta, almoco, nota=1)
    registrar(outra_conta, almoco, nota=5)

    assert Avaliacao.objects.count() == 2


def test_avaliacao_da_mesma_conta_em_outra_refeicao_nao_e_editada(conta, almoco):
    jantar = criar_refeicao(almoco.campus, TERCA, TipoRefeicao.JANTAR)
    registrar(conta, almoco, nota=1)

    registrar(conta, jantar, nota=5, agora=em_brasilia(TERCA, time(18, 0)))

    assert sorted(Avaliacao.objects.values_list("nota", flat=True)) == [1, 5]


def test_corrida_na_primeira_avaliacao_vira_edicao(conta, almoco):
    """Duplo toque: as duas requisições não acham avaliação e tentam inserir.

    A segunda bate no UNIQUE e edita a que a primeira gravou.
    """
    avaliar(conta, almoco, nota=1)
    buscar = AvaliacaoRepository.buscar_por_conta_e_refeicao
    chamadas = []

    def primeira_busca_nao_acha(self, *args, **kwargs):
        chamadas.append(args)
        if len(chamadas) == 1:
            return None
        return buscar(self, *args, **kwargs)

    with mock.patch.object(
        AvaliacaoRepository, "buscar_por_conta_e_refeicao", primeira_busca_nao_acha
    ):
        registrada = registrar(conta, almoco, nota=5)

    assert registrada.criada is False
    assert Avaliacao.objects.get().nota == 5


def test_integrity_error_sem_avaliacao_gravada_nao_vira_edicao(conta, almoco):
    """Se o erro não foi o UNIQUE (não há avaliação para editar), ele sobe."""
    with (
        mock.patch.object(Avaliacao, "save", side_effect=IntegrityError("outra")),
        pytest.raises(IntegrityError),
    ):
        registrar(conta, almoco)


# --- recusas -----------------------------------------------------------------


def test_refeicao_de_outro_dia_e_recusada_sem_gravar(conta, gama):
    segunda = criar_refeicao(gama, SEGUNDA)

    with pytest.raises(AvaliacaoIndisponivelError):
        registrar(conta, segunda)

    assert not Avaliacao.objects.exists()


def test_refeicao_que_ainda_nao_comecou_e_recusada(conta, gama):
    jantar = criar_refeicao(gama, TERCA, TipoRefeicao.JANTAR)

    with pytest.raises(AvaliacaoIndisponivelError):
        registrar(conta, jantar)


def test_edicao_depois_da_meia_noite_e_recusada(conta, almoco):
    avaliar(conta, almoco, nota=2)

    with pytest.raises(AvaliacaoIndisponivelError):
        registrar(conta, almoco, nota=5, agora=DURANTE_O_ALMOCO + timedelta(days=1))

    assert Avaliacao.objects.get().nota == 2


def test_nota_invalida_e_recusada_sem_gravar(conta, almoco):
    with pytest.raises(NotaInvalidaError):
        registrar(conta, almoco, nota=None)

    assert not Avaliacao.objects.exists()


def test_comentario_longo_e_recusado_sem_gravar(conta, almoco):
    with pytest.raises(ComentarioMuitoLongoError):
        registrar(conta, almoco, comentario="a" * 501)

    assert not Avaliacao.objects.exists()


def test_janela_e_conferida_antes_da_nota(conta, gama):
    """Refeição fechada e nota inválida: vale o motivo de indisponível."""
    segunda = criar_refeicao(gama, SEGUNDA)

    with pytest.raises(AvaliacaoIndisponivelError):
        registrar(conta, segunda, nota=0)


# --- pontuação ---------------------------------------------------------------


def test_chama_a_pontuacao_com_a_refeicao_avaliada(conta, outra_conta, almoco):
    # Ids de avaliação e de refeição diferentes, para não confundir os dois.
    avaliar(outra_conta, criar_refeicao(almoco.campus, TERCA, TipoRefeicao.CAFE))
    with mock.patch.object(
        PontuacaoService, "registrar_contribuicao", return_value=ResultadoPontuacao()
    ) as pontuar:
        registrada = registrar(conta, almoco)

    pontuar.assert_called_once_with(
        conta,
        TipoContribuicao.AVALIACAO,
        registrada.avaliacao.id,
        RefeicaoRef(campus=almoco.campus, tipo_refeicao="almoco", data=TERCA),
    )
    assert registrada.avaliacao.id != almoco.id


def test_devolve_os_pontos_da_gamificacao(conta, almoco):
    pontos = ResultadoPontuacao(contribuicao=5)
    with mock.patch.object(
        PontuacaoService, "registrar_contribuicao", return_value=pontos
    ):
        registrada = registrar(conta, almoco)

    assert registrada.pontos is pontos


def test_edicao_chega_a_pontuacao_com_a_mesma_avaliacao(conta, almoco):
    """Quem impede os pontos em dobro é o marcador da Gamificação (ADR 0011):
    a edição só pode chegar lá com a mesma avaliação, nunca com uma nova."""
    with mock.patch.object(
        PontuacaoService, "registrar_contribuicao", return_value=ResultadoPontuacao()
    ) as pontuar:
        primeira = registrar(conta, almoco, nota=2)
        registrar(conta, almoco, nota=5)

    origens = [chamada.args[2] for chamada in pontuar.call_args_list]
    assert origens == [primeira.avaliacao.id, primeira.avaliacao.id]


def test_refeicao_de_outro_campus_vai_com_o_campus_dela(conta, almoco):
    """RN09: a refeição da pontuação é a avaliada, nunca outra."""
    darcy = criar_campus("Darcy Ribeiro")
    almoco_darcy = criar_refeicao(darcy, TERCA)
    with mock.patch.object(
        PontuacaoService, "registrar_contribuicao", return_value=ResultadoPontuacao()
    ) as pontuar:
        registrar(conta, almoco_darcy)

    assert pontuar.call_args.args[3].campus == darcy


def test_recusa_nao_chama_a_pontuacao(conta, gama):
    segunda = criar_refeicao(gama, SEGUNDA)
    with (
        mock.patch.object(PontuacaoService, "registrar_contribuicao") as pontuar,
        pytest.raises(AvaliacaoIndisponivelError),
    ):
        registrar(conta, segunda)

    pontuar.assert_not_called()


def test_falha_na_pontuacao_desfaz_a_avaliacao_nova(conta, almoco):
    with (
        mock.patch.object(
            PontuacaoService, "registrar_contribuicao", side_effect=RuntimeError
        ),
        pytest.raises(RuntimeError),
    ):
        registrar(conta, almoco)

    assert not Avaliacao.objects.exists()


def test_falha_na_pontuacao_desfaz_a_edicao(conta, almoco):
    avaliar(conta, almoco, nota=2, comentario="Frio")
    with (
        mock.patch.object(
            PontuacaoService, "registrar_contribuicao", side_effect=RuntimeError
        ),
        pytest.raises(RuntimeError),
    ):
        registrar(conta, almoco, nota=5, comentario="Quente")

    avaliacao = Avaliacao.objects.get()
    assert (avaliacao.nota, avaliacao.comentario, avaliacao.editada_em) == (
        2,
        "Frio",
        None,
    )
