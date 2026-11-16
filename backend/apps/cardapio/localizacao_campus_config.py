"""Leitura da tabela CAMPUS para a lista pública (Exposição N4 4b)."""

from apps.cardapio.models import Campus


class LocalizacaoCampusConfig:
    """Lê a tabela CAMPUS (fixture da BD-03, valores do Anexo A).

    Fica no app cardapio, e não em config/parametros.py, porque lê do banco
    (BD-04). Na v1 (BE-08) só lista os campi. O centro e o raio de detecção
    (ADR 0009) entram na BE-E3.
    """

    @staticmethod
    def campi():
        """Todos os campi, em ordem de id.

        A ordem é fixa porque o ETag da CampiView é o hash do JSON: ordem
        diferente mudaria o hash. É por id, e não por nome, para continuar
        estável se um nome for corrigido.
        """
        return Campus.objects.order_by("id")
