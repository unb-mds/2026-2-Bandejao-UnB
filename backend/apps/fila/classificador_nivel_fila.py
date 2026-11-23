"""ClassificadorNivelFila: o nível de uma faixa pelos cortes do Anexo A (RN06)."""

from enum import StrEnum
from fractions import Fraction

from config.parametros import ParametrosFilaConfig


class NivelFila(StrEnum):
    VAZIA = "vazia"
    CURTA = "curta"
    MODERADA = "moderada"
    LONGA = "longa"


class ClassificadorNivelFila:
    def classificar(self, media_faixa: Fraction, media_maxima: Fraction) -> NivelFila:
        """Razão entre a média da faixa e a da faixa mais cheia: menos de 25%
        é vazia, menos de 50% curta, menos de 75% moderada, e o resto longa.

        `media_maxima` é sempre maior que zero: a suficiência de dados roda
        antes (Fila N4 4c).
        """
        razao = Fraction(media_faixa) / Fraction(media_maxima)
        niveis = (NivelFila.VAZIA, NivelFila.CURTA, NivelFila.MODERADA)
        for nivel, corte in zip(niveis, ParametrosFilaConfig.cortes, strict=True):
            if razao < Fraction(corte, 100):
                return nivel
        return NivelFila.LONGA
