"""ConfirmacaoLocalizacaoService: o aparelho está no RU? (RF12, Fila N4 4a)."""

from apps.cardapio.models import Campus
from apps.fila.distancia_geografica import Coordenadas, DistanciaGeografica
from apps.fila.erros import LocalizacaoNaoConfirmadaError
from apps.fila.localizacao_ru_config import LocalizacaoRUConfig


class ConfirmacaoLocalizacaoService:
    def __init__(self):
        self.distancia = DistanciaGeografica()

    def confirmar(self, campus: Campus, coordenadas: Coordenadas) -> None:
        """Retorna sem valor se a posição está no raio do RU do campus.

        Lança `LocalizacaoNaoConfirmadaError` se a confirmação está desativada
        no campus (nem calcula a distância: raio zero nunca autoriza, BD-03) ou
        se a posição está além do raio. A borda do raio conta como dentro.
        As coordenadas não são guardadas nem registradas (RI09).
        """
        if not LocalizacaoRUConfig.confirmacao_ativa(campus):
            raise LocalizacaoNaoConfirmadaError
        distancia = self.distancia.metros(
            LocalizacaoRUConfig.centro(campus), coordenadas
        )
        if distancia > LocalizacaoRUConfig.raio_metros(campus):
            raise LocalizacaoNaoConfirmadaError
