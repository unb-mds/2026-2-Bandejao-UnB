"""Patente: os níveis da gamificação (RF26.1, RN11, Gamificação N4 4b).

A ordem dos membros é a dos limiares da `ParametrosGamificacaoConfig`: o
primeiro membro vale a partir do primeiro limiar, e assim por diante. Os
valores são os do contrato (`patente` em GET /api/gamificacao/progresso/).
"""

from enum import StrEnum


class Patente(StrEnum):
    CALOURO_DE_BANDEJA = "CALOURO_DE_BANDEJA"
    RATO_DE_RU = "RATO_DE_RU"
    VETERANO = "VETERANO"
    MESTRE_DA_FILA = "MESTRE_DA_FILA"
    LENDA_DO_RU = "LENDA_DO_RU"
