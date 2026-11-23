"""PontuacaoService (Gamificação N4 4a): a única porta de entrada para pontuar.

`inicializar_conta` (BE-05) é chamada pelo cadastro e `registrar_contribuicao`
pelo check-in e pela avaliação, sempre na transação de quem chama. A regra é
a da BE-14: cada contribuição vale os pontos que a `PontuacaoPolicy` dá ao
tipo; a avaliação só pontua com check-in na mesma refeição (campus + tipo +
data); tudo uma vez só, no campus e no semestre da refeição (RN09, RN12,
Anexo A, ADR 0011).
"""

from django.utils import timezone

from apps.gamificacao.contribuicao import (
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)
from apps.gamificacao.erros import OrigemContribuicaoNaoEncontradaError
from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.origem_contribuicao_repository import (
    OrigemContribuicaoRepository,
)
from apps.gamificacao.pontuacao_policy import PontuacaoPolicy
from apps.gamificacao.pontuacao_repository import PontuacaoRepository
from apps.gamificacao.semestre_resolver import SemestreResolver

# Quem chama importa os tipos daqui (Fila, Avaliação e os testes).
__all__ = [
    "PontuacaoService",
    "RefeicaoRef",
    "ResultadoPontuacao",
    "TipoContribuicao",
]


class PontuacaoService:
    def __init__(self):
        self.pontuacoes = PontuacaoRepository()
        self.origens = OrigemContribuicaoRepository()
        self.politica = PontuacaoPolicy()
        self.semestres = SemestreResolver()

    def inicializar_conta(self, conta) -> None:
        """Cria a `PontuacaoUsuario` da conta nova, com zero ponto.

        Assim a trava da pontuação (`select_for_update`) sempre encontra a
        linha (Cadastro N4 4a, Gamificação N4).
        """
        PontuacaoUsuario.objects.create(usuario=conta)

    def travar_conta(self, conta) -> None:
        """Trava a pontuação da conta até o fim da transação de quem chama.

        Para quem trava, antes de pontuar, uma linha que a pontuação também
        escreve: a Avaliação trava a avaliação para editá-la, e a pontuação
        de um check-in marca essa mesma avaliação. Travando a conta primeiro,
        as duas transações pegam as travas na mesma ordem e não se prendem
        uma na outra (deadlock). `registrar_contribuicao` trava de novo, sem
        custo, então quem não precisa disto não precisa chamar.
        """
        self.pontuacoes.travar_por_conta(conta)

    def registrar_contribuicao(
        self,
        conta,
        tipo: TipoContribuicao,
        origem_id: int,
        refeicao: RefeicaoRef,
    ) -> ResultadoPontuacao:
        """Única porta de entrada para pontuar (Gamificação N4 4a).

        Roda dentro da transação de quem chama (Fila ou Avaliação), sem abrir
        outra nem fazer commit: se algo falhar, contribuição e pontos voltam
        juntos (ADR 0011). Os passos, na ordem:

        1. trava a pontuação da conta (primeira leitura, sempre);
        2. registro de origem já pontuado: 0, uma vez só;
        3. avaliação: oculta pela moderação, 0 e nunca pontua; sem check-in na
           mesma refeição, 0 sem marcar, e os pontos vêm com o check-in (RN09);
        4. marca o registro e soma os pontos do tipo ao total e ao semestre do
           campus da refeição. Se o registro não existe (ou é de outro tipo),
           nada é marcado nem somado: `OrigemContribuicaoNaoEncontradaError`;
        5. no check-in, libera a avaliação feita antes, na mesma refeição.
        """
        agora = timezone.now()
        pontuacao = self.pontuacoes.travar_por_conta(conta)
        if self.origens.ja_pontuada(tipo, origem_id):
            return ResultadoPontuacao()
        if tipo == TipoContribuicao.AVALIACAO and not self._avaliacao_pontua(
            conta, origem_id, refeicao
        ):
            return ResultadoPontuacao()

        contribuicao = self.politica.pontos_por(tipo)
        self._marcar(tipo, origem_id, agora)
        liberada = 0
        if tipo == TipoContribuicao.CHECKIN:
            avaliacao = self.origens.avaliacao_nao_pontuada(conta, refeicao)
            if avaliacao is not None:
                liberada = self.politica.pontos_por(TipoContribuicao.AVALIACAO)
                self._marcar(TipoContribuicao.AVALIACAO, avaliacao.id, agora)
        # Check-in e avaliação liberada são da mesma refeição: mesmo campus e
        # mesmo semestre, então uma gravação só de cada contador.
        self._conceder(pontuacao, conta, refeicao, contribuicao + liberada)
        return ResultadoPontuacao(
            contribuicao=contribuicao, avaliacao_liberada=liberada
        )

    def _marcar(self, tipo: TipoContribuicao, origem_id: int, agora) -> None:
        """ "Uma vez só" depende desta gravação: sem ela, nada de pontos."""
        if not self.origens.marcar_pontuada(tipo, origem_id, agora):
            raise OrigemContribuicaoNaoEncontradaError(tipo, origem_id)

    def _avaliacao_pontua(self, conta, origem_id: int, refeicao: RefeicaoRef) -> bool:
        """A avaliação pontua se não está oculta pela moderação e a refeição já
        tem check-in confirmado da conta. Pontos concedidos antes de ocultar
        não são retirados (ajuste manual, ADR 0004)."""
        return not self.origens.avaliacao_oculta(
            origem_id
        ) and self.origens.tem_checkin_confirmado(conta, refeicao)

    def _conceder(self, pontuacao, conta, refeicao: RefeicaoRef, pontos: int) -> None:
        pontuacao.pontos_totais += pontos
        self.pontuacoes.salvar(pontuacao)
        self.pontuacoes.somar_pontos_semestre(
            conta, refeicao.campus, self.semestres.semestre_de(refeicao.data), pontos
        )
