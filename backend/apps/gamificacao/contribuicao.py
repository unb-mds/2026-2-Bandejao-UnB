"""Tipos da contribuição pontuável (Gamificação N4 4a).

Ficam fora do `pontuacao_service.py` porque a `PontuacaoPolicy` e o
`OrigemContribuicaoRepository` também usam `TipoContribuicao`, e o serviço
importa os dois: no mesmo módulo, o import seria circular. Quem chama a
pontuação continua importando tudo de `apps.gamificacao.pontuacao_service`.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from apps.cardapio.models import Campus, TipoRefeicao


class TipoContribuicao(StrEnum):
    CHECKIN = "checkin"
    RESPOSTA_SAIDA = "resposta_saida"
    AVALIACAO = "avaliacao"


@dataclass(frozen=True)
class RefeicaoRef:
    """A refeição da contribuição, tirada do registro já gravado (RN09)."""

    campus: Campus
    tipo_refeicao: TipoRefeicao
    data: date


@dataclass(frozen=True)
class ResultadoPontuacao:
    """Pontos concedidos agora, para o bloco `pontos` da resposta (RF24.2)."""

    contribuicao: int = 0
    avaliacao_liberada: int = 0

    @property
    def total(self) -> int:
        return self.contribuicao + self.avaliacao_liberada
