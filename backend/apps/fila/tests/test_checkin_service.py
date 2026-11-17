"""CheckinService.registrar (BE-09, RF11, RF12, RI03, Fila N4 4a).

Ordem das conferências: aviso de privacidade (sem gravar tentativa), horário,
duplicidade e distância ao RU. Toda tentativa conferida grava uma
`TentativaCheckin`; o check-in confirmado e a pontuação ficam na mesma
transação.
"""

from datetime import UTC, date, datetime, time
from unittest import mock

import pytest

from apps.cardapio.models import TipoRefeicao
from apps.fila.checkin_repository import CheckinRepository
from apps.fila.checkin_service import CheckinService
from apps.fila.confirmacao_localizacao_service import ConfirmacaoLocalizacaoService
from apps.fila.erros import (
    AvisoPrivacidadePendenteError,
    CheckinDuplicadoError,
    CheckinForaDoHorarioError,
    LocalizacaoNaoConfirmadaError,
)
from apps.fila.janela_checkin_validator import JanelaCheckinValidator
from apps.fila.models import (
    Checkin,
    MotivoRejeicao,
    ResultadoTentativa,
    TentativaCheckin,
)
from apps.fila.tests.apoio import RU_DARCY, RU_GAMA, ao_norte
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)

pytestmark = pytest.mark.django_db

# 12h07 em Brasília, terça-feira 17/11/2026: dentro do almoço.
AGORA = datetime(2026, 11, 17, 15, 7, tzinfo=UTC)
# 16h em Brasília: entre o almoço e o jantar.
FORA_DO_HORARIO = datetime(2026, 11, 17, 19, 0, tzinfo=UTC)
NO_RU = ao_norte(RU_DARCY, 20)
LONGE = ao_norte(RU_DARCY, 500)
ALMOCO = TipoRefeicao.ALMOCO


def registrar(conta, campus, coordenadas=NO_RU, agora=AGORA, tipo=ALMOCO):
    return CheckinService().registrar(conta, campus, tipo, coordenadas, agora)


def gps_nao_pode_ser_consultado():
    return mock.patch.object(
        ConfirmacaoLocalizacaoService,
        "confirmar",
        side_effect=AssertionError("o GPS foi conferido antes da hora"),
    )


def unica_tentativa():
    assert TentativaCheckin.objects.count() == 1
    return TentativaCheckin.objects.get()


# --- Confirmado --------------------------------------------------------------


def test_confirmado_grava_o_checkin_da_refeicao(conta, darcy):
    registrado = registrar(conta, darcy)

    checkin = Checkin.objects.get()
    assert registrado.checkin == checkin
    assert checkin.usuario == conta
    assert checkin.campus == darcy
    assert checkin.tipo_refeicao == ALMOCO
    assert checkin.data == date(2026, 11, 17)
    assert checkin.registrado_em == AGORA
    assert checkin.tempo_espera_min is None


def test_data_e_o_dia_de_brasilia_e_nao_o_de_utc(conta, darcy):
    """22h de 17/11 em Brasília já é 18/11 em UTC.

    Nenhuma refeição do Anexo A vai tão tarde; o horário é liberado no teste
    para a regra valer mesmo se o Anexo A mudar.
    """
    noite = datetime(2026, 11, 18, 1, 0, tzinfo=UTC)
    with mock.patch.object(
        JanelaCheckinValidator, "dentro_do_horario", return_value=True
    ):
        registrar(conta, darcy, agora=noite, tipo=TipoRefeicao.JANTAR)

    assert Checkin.objects.get().data == date(2026, 11, 17)
    assert TentativaCheckin.objects.get().data == date(2026, 11, 17)


@pytest.mark.parametrize(
    "hora_utc, faixa",
    [
        (time(15, 7), time(12, 0)),
        (time(15, 15), time(12, 15)),
        (time(15, 29, 59), time(12, 15)),
        (time(14, 0), time(11, 0)),
    ],
)
def test_faixa_inicio_e_o_inicio_da_faixa_de_15_min_no_horario_local(
    conta, darcy, hora_utc, faixa
):
    """RF13: a previsão agrupa os check-ins em faixas de 15 min de Brasília."""
    registrar(conta, darcy, agora=datetime.combine(AGORA.date(), hora_utc, UTC))

    assert Checkin.objects.get().faixa_inicio == faixa


def test_confirmado_grava_tentativa_confirmada_sem_motivo(conta, darcy):
    registrar(conta, darcy)

    tentativa = unica_tentativa()
    assert tentativa.usuario == conta
    assert tentativa.campus == darcy
    assert tentativa.tipo_refeicao == ALMOCO
    assert tentativa.data == date(2026, 11, 17)
    assert tentativa.data_hora == AGORA
    assert tentativa.resultado == ResultadoTentativa.CONFIRMADO
    assert tentativa.motivo is None


def test_confirmado_pontua_com_a_refeicao_do_proprio_checkin(conta, darcy):
    """RN09: campus, tipo e data da pontuação são os do check-in gravado."""
    pontos = ResultadoPontuacao(contribuicao=10, avaliacao_liberada=5)
    with mock.patch.object(
        PontuacaoService, "registrar_contribuicao", return_value=pontos
    ) as pontuar:
        registrado = registrar(conta, darcy)

    checkin = Checkin.objects.get()
    pontuar.assert_called_once_with(
        conta,
        TipoContribuicao.CHECKIN,
        checkin.id,
        RefeicaoRef(campus=darcy, tipo_refeicao=ALMOCO, data=date(2026, 11, 17)),
    )
    assert registrado.pontos == pontos
    assert registrado.pontos.total == 15


@pytest.mark.django_db(transaction=True)
def test_se_a_pontuacao_falhar_nada_e_gravado(conta, darcy):
    """Fila N4 4a: check-in e pontos na mesma transação (ADR 0011)."""
    with (
        mock.patch.object(
            PontuacaoService,
            "registrar_contribuicao",
            side_effect=RuntimeError("falhou"),
        ),
        pytest.raises(RuntimeError),
    ):
        registrar(conta, darcy)

    assert not Checkin.objects.exists()
    assert not TentativaCheckin.objects.exists()


# --- Passo 0: aviso de privacidade -------------------------------------------


def test_aviso_pendente_recusa_sem_gravar_tentativa(conta, darcy):
    conta.versao_aviso_aceita = "2020-01-01"

    with pytest.raises(AvisoPrivacidadePendenteError):
        registrar(conta, darcy)

    assert not TentativaCheckin.objects.exists()
    assert not Checkin.objects.exists()


def test_aviso_pendente_vem_antes_do_horario(conta, darcy):
    conta.versao_aviso_aceita = "2020-01-01"

    with gps_nao_pode_ser_consultado(), pytest.raises(AvisoPrivacidadePendenteError):
        registrar(conta, darcy, agora=FORA_DO_HORARIO)

    assert not TentativaCheckin.objects.exists()


# --- Passo 1: horário --------------------------------------------------------


def test_fora_do_horario_grava_tentativa_e_nao_consulta_o_gps(conta, darcy):
    with gps_nao_pode_ser_consultado(), pytest.raises(CheckinForaDoHorarioError):
        registrar(conta, darcy, agora=FORA_DO_HORARIO)

    tentativa = unica_tentativa()
    assert tentativa.resultado == ResultadoTentativa.REJEITADO
    assert tentativa.motivo == MotivoRejeicao.FORA_DO_HORARIO
    assert tentativa.data_hora == FORA_DO_HORARIO
    assert not Checkin.objects.exists()


def test_fora_do_horario_vem_antes_da_duplicidade(conta, darcy):
    registrar(conta, darcy)

    with pytest.raises(CheckinForaDoHorarioError):
        registrar(conta, darcy, agora=FORA_DO_HORARIO)


def test_erro_de_horario_diz_a_janela_da_refeicao(conta, darcy):
    with pytest.raises(CheckinForaDoHorarioError) as erro:
        registrar(conta, darcy, agora=FORA_DO_HORARIO)

    assert (erro.value.inicio, erro.value.fim) == (time(11, 0), time(14, 30))


# --- Passo 2: duplicidade ----------------------------------------------------


def test_checkin_repetido_grava_tentativa_e_nao_consulta_o_gps(conta, darcy):
    registrar(conta, darcy)

    with gps_nao_pode_ser_consultado(), pytest.raises(CheckinDuplicadoError):
        registrar(conta, darcy, agora=AGORA.replace(minute=40))

    assert Checkin.objects.count() == 1
    ultima = TentativaCheckin.objects.latest("id")
    assert ultima.resultado == ResultadoTentativa.REJEITADO
    assert ultima.motivo == MotivoRejeicao.CHECKIN_DUPLICADO


def test_outra_refeicao_do_mesmo_dia_nao_e_repetida(conta, darcy):
    registrar(conta, darcy)

    registrar(
        conta,
        darcy,
        tipo=TipoRefeicao.JANTAR,
        agora=datetime(2026, 11, 17, 21, 0, tzinfo=UTC),
    )

    assert Checkin.objects.count() == 2


def test_mesma_refeicao_em_outro_dia_nao_e_repetida(conta, darcy):
    registrar(conta, darcy)

    registrar(conta, darcy, agora=AGORA.replace(day=18))

    assert Checkin.objects.count() == 2


def test_tentativa_recusada_por_localizacao_nao_conta_como_checkin(conta, darcy):
    """RF11: quem estava fora do raio tenta de novo depois de chegar."""
    with pytest.raises(LocalizacaoNaoConfirmadaError):
        registrar(conta, darcy, coordenadas=LONGE)

    registrar(conta, darcy, agora=AGORA.replace(minute=20))

    assert Checkin.objects.count() == 1


# --- Corrida: o UNIQUE do banco decide (RI03) --------------------------------


def livre_na_primeira_consulta():
    """A primeira consulta diz "não existe"; as seguintes consultam o banco.

    Simula o duplo toque: a outra requisição gravou entre a consulta e o
    INSERT desta.
    """
    original = CheckinRepository.existe_checkin
    chamadas = []

    def consultar(self, *args):
        chamadas.append(args)
        return False if len(chamadas) == 1 else original(self, *args)

    return mock.patch.object(
        CheckinRepository, "existe_checkin", autospec=True, side_effect=consultar
    )


def test_duas_requisicoes_simultaneas_gravam_um_checkin_so(conta, darcy):
    registrar(conta, darcy)

    with livre_na_primeira_consulta(), pytest.raises(CheckinDuplicadoError):
        registrar(conta, darcy)

    assert Checkin.objects.count() == 1
    motivos = list(TentativaCheckin.objects.order_by("id").values_list("motivo"))
    assert motivos == [(None,), (MotivoRejeicao.CHECKIN_DUPLICADO,)]


def test_corrida_nao_pontua_de_novo(conta, darcy):
    registrar(conta, darcy)

    with (
        livre_na_primeira_consulta(),
        mock.patch.object(PontuacaoService, "registrar_contribuicao") as pontuar,
        pytest.raises(CheckinDuplicadoError),
    ):
        registrar(conta, darcy)

    pontuar.assert_not_called()


# --- Passo 3: distância ao RU ------------------------------------------------


def test_fora_do_raio_grava_tentativa_e_nao_pontua(conta, darcy):
    with (
        mock.patch.object(PontuacaoService, "registrar_contribuicao") as pontuar,
        pytest.raises(LocalizacaoNaoConfirmadaError),
    ):
        registrar(conta, darcy, coordenadas=LONGE)

    tentativa = unica_tentativa()
    assert tentativa.resultado == ResultadoTentativa.REJEITADO
    assert tentativa.motivo == MotivoRejeicao.LOCALIZACAO_NAO_CONFIRMADA
    assert not Checkin.objects.exists()
    pontuar.assert_not_called()


def test_no_ru_de_outro_campus_nao_confirma(conta, darcy, gama):
    with pytest.raises(LocalizacaoNaoConfirmadaError):
        registrar(conta, darcy, coordenadas=RU_GAMA)

    assert not Checkin.objects.exists()


def test_no_ru_do_proprio_campus_confirma(conta, darcy, gama):
    registrar(conta, gama, coordenadas=RU_GAMA)

    assert Checkin.objects.get().campus == gama
