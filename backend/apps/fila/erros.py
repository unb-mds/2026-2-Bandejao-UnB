"""Erros do check-in (Fila N4 4a).

A `CheckinView` traduz cada um para o contrato:
- `AvisoPrivacidadePendenteError` -> 403 `aviso_privacidade_pendente`;
- `CheckinRecusadoError` (e as subclasses) -> 422 com o `motivo` como `codigo`.
"""

from datetime import time

from apps.fila.models import MotivoRejeicao


class AvisoPrivacidadePendenteError(Exception):
    """Falta a ciência do aviso de privacidade atual (RF11, RNF07.1).

    Não é uma tentativa de check-in: nada é gravado.
    """


class CheckinRecusadoError(Exception):
    """Tentativa conferida e recusada. Grava uma `TentativaCheckin` com o
    `motivo` (RF12)."""

    motivo: MotivoRejeicao


class CheckinForaDoHorarioError(CheckinRecusadoError):
    """Fora do horário da refeição (Anexo A). Leva a janela para a mensagem."""

    motivo = MotivoRejeicao.FORA_DO_HORARIO

    def __init__(self, inicio: time, fim: time):
        super().__init__(inicio, fim)
        self.inicio = inicio
        self.fim = fim


class CheckinDuplicadoError(CheckinRecusadoError):
    """Já existe check-in desta conta na mesma refeição (RI03)."""

    motivo = MotivoRejeicao.CHECKIN_DUPLICADO


class LocalizacaoNaoConfirmadaError(CheckinRecusadoError):
    """Fora do raio do RU, ou confirmação desativada no campus (RF12, BD-03)."""

    motivo = MotivoRejeicao.LOCALIZACAO_NAO_CONFIRMADA
