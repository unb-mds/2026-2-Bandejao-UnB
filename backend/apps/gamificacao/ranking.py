"""Ranking: as linhas que o RankingService produz e o que GET
/api/ranking/{campusId}/ devolve (RF27.2, RN12, Gamificação N4 4c).

`LinhaRanking` é interna e tem os pontos; `LinhaRankingPublica` é a única
forma que sai para terceiros, sem pontos (RI10, RI12, ADR 0008). Sem
`distintivo` nesta Release (backlog, seção 3, item 6).
"""

from dataclasses import dataclass

from apps.gamificacao.patente import Patente


@dataclass(frozen=True)
class LinhaRanking:
    # A conta vem com a `pontuacao` carregada (patente dos pontos totais).
    conta: object
    posicao: int
    # Pontos do semestre no campus: ordenam o ranking e nunca saem.
    pontos: int


@dataclass(frozen=True)
class LinhaRankingPublica:
    posicao: int
    apelido: str
    patente: Patente
