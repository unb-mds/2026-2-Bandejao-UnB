"""Coordenadas e distância entre dois pontos (RF12, Fila N4 4a)."""

import math
from dataclasses import dataclass

# Raio médio da Terra (IUGG). Para os raios de 150 m do RU, o erro de tratar a
# Terra como esfera fica bem abaixo do erro do GPS do celular.
RAIO_DA_TERRA_METROS = 6_371_008.8


@dataclass(frozen=True, slots=True)
class Coordenadas:
    """Posição em graus decimais. Transitória: nunca é gravada (RI09).

    O `repr` esconde os valores para a posição não aparecer num log ou num
    traceback por descuido.
    """

    latitude: float
    longitude: float

    def __repr__(self):
        return "Coordenadas(<omitidas>)"


class DistanciaGeografica:
    def metros(self, a: Coordenadas, b: Coordenadas) -> float:
        """Distância em linha reta sobre a superfície (fórmula de haversine)."""
        lat_a, lat_b = math.radians(a.latitude), math.radians(b.latitude)
        delta_lat = lat_b - lat_a
        delta_lng = math.radians(b.longitude - a.longitude)
        h = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lng / 2) ** 2
        )
        return 2 * RAIO_DA_TERRA_METROS * math.asin(math.sqrt(h))
