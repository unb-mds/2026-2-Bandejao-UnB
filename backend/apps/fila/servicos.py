"""PROVA DO CI (BE-02): codigo sem teste para a porta de cobertura barrar."""

from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_M = 6_371_000


def distancia_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_M * asin(sqrt(a))


def dentro_do_raio(lat, lon, centro_lat, centro_lon, raio_m):
    if raio_m <= 0:
        raise ValueError("raio_m precisa ser positivo")
    distancia = distancia_m(lat, lon, centro_lat, centro_lon)
    return distancia <= raio_m


def nivel_da_fila(chegadas, maximo):
    if maximo == 0:
        return "sem dados"
    proporcao = chegadas / maximo
    if proporcao >= 0.8:
        return "pico"
    if proporcao >= 0.5:
        return "moderado"
    return "tranquilo"
