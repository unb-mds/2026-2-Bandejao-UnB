"""PontuacaoService (Gamificação N4).

Versão mínima: `inicializar_conta` (BE-05), chamada pelo cadastro na mesma
transação, e `registrar_contribuicao` (BE-09), chamada pelo check-in na mesma
transação, que ainda não concede pontos. A BE-14 acrescenta a regra dos
pontos e os outros métodos (`apagar_contadores`...) sem mudar a assinatura
destes dois.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from apps.cardapio.models import Campus
from apps.gamificacao.models import PontuacaoUsuario


class TipoContribuicao(StrEnum):
    CHECKIN = "checkin"
    RESPOSTA_SAIDA = "resposta_saida"
    AVALIACAO = "avaliacao"


@dataclass(frozen=True)
class RefeicaoRef:
    """A refeição da contribuição, tirada do registro já gravado (RN09)."""

    campus: Campus
    tipo_refeicao: str
    data: date


@dataclass(frozen=True)
class ResultadoPontuacao:
    """Pontos concedidos agora, para o bloco `pontos` da resposta (RF24.2)."""

    contribuicao: int = 0
    avaliacao_liberada: int = 0

    @property
    def total(self) -> int:
        return self.contribuicao + self.avaliacao_liberada


class PontuacaoService:
    def inicializar_conta(self, conta) -> None:
        """Cria a `PontuacaoUsuario` da conta nova, com zero ponto.

        Assim a trava da pontuação (`select_for_update`) sempre encontra a
        linha (Cadastro N4 4a, Gamificação N4).
        """
        PontuacaoUsuario.objects.create(usuario=conta)

    def registrar_contribuicao(
        self,
        conta,
        tipo: TipoContribuicao,
        origem_id: int,
        refeicao: RefeicaoRef,
    ) -> ResultadoPontuacao:
        """Única porta de entrada para pontuar (Gamificação N4 4a).

        Por enquanto não grava nada e devolve zero ponto: com `total` 0 o PWA
        não mostra o aviso (RF24.2). A BE-14 implementa a trava por conta, o
        marcador `pontos_concedidos_em` e os valores do Anexo A.
        """
        return ResultadoPontuacao()
