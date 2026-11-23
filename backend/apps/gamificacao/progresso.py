"""Progresso: o que GET /api/gamificacao/progresso/ devolve (RF26.2,
Gamificação N4 4c).

Só os campos do contrato desta Release: sem `posicoesAtuais`,
`posicoesSemestreAnterior` nem `distintivo` (backlog, seção 3, item 6).
"""

from dataclasses import dataclass

from apps.gamificacao.patente import Patente


@dataclass(frozen=True)
class Progresso:
    patente: Patente
    pontos_totais: int
    falta_para_proxima: int
    # Os três abaixo ficam como estão até a sequência semanal (BE-E6).
    sequencia: int
    dias_na_semana: int
    minimo_dias: int
    participa_ranking: bool
