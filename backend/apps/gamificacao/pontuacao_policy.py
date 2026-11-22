"""PontuacaoPolicy: quantos pontos vale cada tipo de contribuição (Anexo A)."""

from apps.gamificacao.contribuicao import TipoContribuicao
from config.parametros import ParametrosGamificacaoConfig


class PontuacaoPolicy:
    def pontos_por(self, tipo: TipoContribuicao) -> int:
        """Os pontos do tipo, e só do tipo (RI11).

        Nota, comentário, horário do check-in e nível da fila não entram: a
        pontuação não pode premiar nota alta nem um horário (ADR 0010).
        """
        return {
            TipoContribuicao.CHECKIN: ParametrosGamificacaoConfig.pontos_checkin,
            TipoContribuicao.RESPOSTA_SAIDA: (
                ParametrosGamificacaoConfig.pontos_resposta_saida
            ),
            TipoContribuicao.AVALIACAO: ParametrosGamificacaoConfig.pontos_avaliacao,
        }[tipo]
