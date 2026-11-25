"""ProgressoService: monta o "Meu progresso" da conta (RF26.1, RF26.2,
Gamificação N4 4c).

Só leitura: não trava nem cria a `PontuacaoUsuario`. Quem cria a linha que
falta é a adesão (`PontuacaoRepository.alterar_adesao`) ou a pontuação.
"""

from datetime import date

from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.patente_resolver import PatenteResolver
from apps.gamificacao.progresso import Progresso
from config.parametros import ParametrosGamificacaoConfig


class ProgressoService:
    def __init__(self):
        self.patentes = PatenteResolver()

    def montar(self, conta, hoje: date) -> Progresso:
        """O progresso da própria conta.

        Sem a `PontuacaoUsuario` (não deveria faltar, a linha nasce com a
        conta), responde como zero ponto e sem adesão. `hoje` ainda não é
        usado: entra pela assinatura do C4 4c e vai servir à sequência
        semanal (BE-E6). Até lá, `sequencia` é a coluna `sequencia_atual`
        (0) e `dias_na_semana` é 0.
        """
        pontuacao = PontuacaoUsuario.objects.filter(usuario=conta).first()
        pontos = pontuacao.pontos_totais if pontuacao else 0
        return Progresso(
            patente=self.patentes.patente(pontos),
            pontos_totais=pontos,
            falta_para_proxima=self.patentes.falta_para_proxima(pontos),
            sequencia=pontuacao.sequencia_atual if pontuacao else 0,
            dias_na_semana=0,
            minimo_dias=ParametrosGamificacaoConfig.min_dias_semana,
            participa_ranking=pontuacao.participa_ranking if pontuacao else False,
        )
