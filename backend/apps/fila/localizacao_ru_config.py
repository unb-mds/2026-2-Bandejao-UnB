"""Leitura da localização do RU na tabela CAMPUS (Fila N4 4a)."""

from apps.cardapio.models import Campus
from apps.fila.distancia_geografica import Coordenadas


class LocalizacaoRUConfig:
    """Lê a confirmação, o centro e o raio do RU de cada campus (BD-03).

    Os valores do Anexo A ficam na tabela CAMPUS (fixture da BD-03), e não em
    config/parametros.py, porque são um por campus. O centro é o do RU
    (`ru_*`), e não o do campus (`centro_*`), que é o da detecção no aparelho
    (ADR 0009).
    """

    @staticmethod
    def confirmacao_ativa(campus: Campus) -> bool:
        return campus.confirmacao_ativa

    @staticmethod
    def centro(campus: Campus) -> Coordenadas:
        return Coordenadas(
            latitude=float(campus.ru_latitude), longitude=float(campus.ru_longitude)
        )

    @staticmethod
    def raio_metros(campus: Campus) -> int:
        return campus.raio_confirmacao_metros
