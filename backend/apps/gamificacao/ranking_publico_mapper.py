"""RankingPublicoMapper: a única saída do ranking para terceiros (RI10, RI12,
ADR 0008, Gamificação N4 4c).

Mesmo padrão do `AvaliacaoPublicaMapper`: posição, apelido e patente, nunca
pontos, matrícula/SIAPE nem e-mail. Sem `distintivo` nesta Release (backlog,
seção 3, item 6), e com ele a seta para o `BandejaOuroResolver`.
"""

from apps.gamificacao.patente_resolver import PatenteResolver
from apps.gamificacao.ranking import LinhaRanking, LinhaRankingPublica


class RankingPublicoMapper:
    def __init__(self, patentes: PatenteResolver | None = None):
        self.patentes = patentes or PatenteResolver()

    def para_publico(self, linha: LinhaRanking) -> LinhaRankingPublica:
        """A patente é a dos pontos totais (a do "Meu progresso", RN11), não
        a dos pontos do semestre que ordenam o ranking."""
        return LinhaRankingPublica(
            posicao=linha.posicao,
            apelido=linha.conta.apelido,
            patente=self.patentes.patente(linha.conta.pontuacao.pontos_totais),
        )
