"""CheckinService: check-in no RU com confirmação por GPS (RF11, RF12, Fila N4 4a)."""

from dataclasses import dataclass
from datetime import date, datetime, time

from django.db import transaction
from django.utils import timezone

from apps.cardapio.models import Campus
from apps.fila.checkin_repository import CheckinRepository
from apps.fila.confirmacao_localizacao_service import ConfirmacaoLocalizacaoService
from apps.fila.distancia_geografica import Coordenadas
from apps.fila.erros import (
    AvisoPrivacidadePendenteError,
    CheckinDuplicadoError,
    CheckinForaDoHorarioError,
    CheckinRecusadoError,
)
from apps.fila.janela_checkin_validator import JanelaCheckinValidator
from apps.fila.models import Checkin, ResultadoTentativa, TentativaCheckin
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)
from config.parametros import ParametrosFilaConfig


@dataclass(frozen=True)
class CheckinRegistrado:
    checkin: Checkin
    pontos: ResultadoPontuacao


def faixa_inicio(agora: datetime) -> time:
    """Início da faixa de 15 min do horário local (RF13): 12h07 vira 12h00."""
    local = timezone.localtime(agora)
    faixa = ParametrosFilaConfig.faixa_minutos
    return time(local.hour, local.minute - local.minute % faixa)


class CheckinService:
    def __init__(self):
        self.janela = JanelaCheckinValidator()
        self.repositorio = CheckinRepository()
        self.confirmacao = ConfirmacaoLocalizacaoService()
        self.pontuacao = PontuacaoService()

    def registrar(
        self,
        conta,
        campus: Campus,
        tipo_refeicao: str,
        coordenadas: Coordenadas,
        agora: datetime,
    ) -> CheckinRegistrado:
        """Confere, na ordem, aviso, horário, duplicidade e localização.

        A ordem vai do mais barato ao mais caro, e uma tentativa que já seria
        recusada por outro motivo não depende do GPS. O aviso pendente não é
        uma tentativa: nada é gravado. Toda tentativa conferida grava uma
        `TentativaCheckin`; a recusada fica fora da transação do check-in.
        """
        if conta.aviso_privacidade_pendente():
            raise AvisoPrivacidadePendenteError
        data = timezone.localdate(agora)
        try:
            self._conferir(conta, campus, tipo_refeicao, coordenadas, agora, data)
            return self._confirmar(conta, campus, tipo_refeicao, agora, data)
        except CheckinRecusadoError as erro:
            self.repositorio.registrar_tentativa(
                self._tentativa(conta, campus, tipo_refeicao, agora, data, erro.motivo)
            )
            raise

    def _conferir(self, conta, campus, tipo_refeicao, coordenadas, agora, data):
        if not self.janela.dentro_do_horario(tipo_refeicao, agora):
            raise CheckinForaDoHorarioError(*self.janela.janela(tipo_refeicao))
        if self.repositorio.existe_checkin(conta, campus, tipo_refeicao, data):
            raise CheckinDuplicadoError
        self.confirmacao.confirmar(campus, coordenadas)

    def _confirmar(self, conta, campus, tipo_refeicao, agora, data):
        """Check-in, tentativa e pontos juntos: se a pontuação falhar, nada fica
        gravado e a pessoa tenta de novo (ADR 0011)."""
        with transaction.atomic():
            checkin = self.repositorio.salvar_checkin(
                Checkin(
                    usuario=conta,
                    campus=campus,
                    tipo_refeicao=tipo_refeicao,
                    data=data,
                    registrado_em=agora,
                    faixa_inicio=faixa_inicio(agora),
                )
            )
            self.repositorio.registrar_tentativa(
                self._tentativa(conta, campus, tipo_refeicao, agora, data)
            )
            # A refeição é a do check-in gravado, nunca um campo do PWA (RN09).
            pontos = self.pontuacao.registrar_contribuicao(
                conta,
                TipoContribuicao.CHECKIN,
                checkin.id,
                RefeicaoRef(campus=campus, tipo_refeicao=tipo_refeicao, data=data),
            )
        return CheckinRegistrado(checkin=checkin, pontos=pontos)

    @staticmethod
    def _tentativa(conta, campus, tipo_refeicao, agora, data: date, motivo=None):
        return TentativaCheckin(
            usuario=conta,
            campus=campus,
            tipo_refeicao=tipo_refeicao,
            data=data,
            data_hora=agora,
            resultado=(
                ResultadoTentativa.CONFIRMADO
                if motivo is None
                else ResultadoTentativa.REJEITADO
            ),
            motivo=motivo,
        )
