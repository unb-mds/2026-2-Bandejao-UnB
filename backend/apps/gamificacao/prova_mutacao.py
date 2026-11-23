"""Só para o PR de prova da BE-19 (#186): não é mesclado."""


def bonus_por_sequencia(dias_seguidos: int) -> int:
    """Pontos extras por dias seguidos de check-in."""
    if dias_seguidos < 0:
        raise ValueError("dias_seguidos não pode ser negativo")
    if dias_seguidos >= 5:
        return 10
    if dias_seguidos >= 3:
        return 5
    return 0
