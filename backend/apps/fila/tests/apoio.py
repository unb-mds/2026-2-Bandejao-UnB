"""Dados de apoio dos testes do check-in (BE-09).

As posições são montadas a partir do RU: andar `metros` para o norte muda só a
latitude, e a distância pela fórmula de haversine é exatamente `metros` (a
menos do arredondamento do float).
"""

import math
from decimal import Decimal

from apps.cardapio.models import Campus
from apps.fila.distancia_geografica import RAIO_DA_TERRA_METROS, Coordenadas

# Valores da fixture da BD-03 (apps/cardapio/fixtures/campi.json).
RU_DARCY = Coordenadas(latitude=-15.764203, longitude=-47.870251)
RU_GAMA = Coordenadas(latitude=-15.989493, longitude=-48.044024)
RAIO = 150


def ao_norte(origem, metros):
    graus = math.degrees(metros / RAIO_DA_TERRA_METROS)
    return Coordenadas(latitude=origem.latitude + graus, longitude=origem.longitude)


def criar_campus(nome="Darcy Ribeiro", ru=RU_DARCY, raio=RAIO, ativa=True):
    """O centro do campus (detecção, ADR 0009) fica a 1 km do RU, para um
    teste pegar quem confundir os dois."""
    centro = ao_norte(ru, 1000)
    return Campus.objects.create(
        nome=nome,
        # Colunas UNIQUE da BD-16 (ADR 0014): o nome, que já é único, serve.
        rotulo_pagina_ru=nome,
        prefixo_arquivo_pdf=nome,
        ru_latitude=Decimal(str(ru.latitude)),
        ru_longitude=Decimal(str(ru.longitude)),
        raio_confirmacao_metros=raio,
        confirmacao_ativa=ativa,
        centro_latitude=Decimal(str(round(centro.latitude, 6))),
        centro_longitude=Decimal(str(round(centro.longitude, 6))),
        raio_deteccao_metros=raio,
    )
