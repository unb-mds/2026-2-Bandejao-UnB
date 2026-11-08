"""Formatos de entrada e saída do app cardapio (contrato OpenAPI, BE-03)."""

from rest_framework import serializers


class CampusPublicoSerializer(serializers.Serializer):
    """Um campus na lista pública (Exposição N4 4b). Só id e nome na v1."""

    id = serializers.IntegerField()
    nome = serializers.CharField()


class PratoFiltradoSerializer(serializers.Serializer):
    """Um prato do cardápio (Exposição N4 4a)."""

    descricao = serializers.CharField()
    marcadores = serializers.ListField(child=serializers.CharField())
    contemMarcadorSelecionado = serializers.BooleanField()


class CategoriaFiltradaSerializer(serializers.Serializer):
    """Uma linha do cardápio, com os pratos que sobraram nos filtros."""

    nome = serializers.CharField()
    semOpcaoCompativel = serializers.BooleanField(
        help_text="true se todos os pratos da categoria têm marcador selecionado.",
    )
    pratos = PratoFiltradoSerializer(many=True)


class CardapioFiltradoSerializer(serializers.Serializer):
    """Resposta do GET /api/cardapio/ (Exposição N4 4a)."""

    campus = serializers.IntegerField(
        help_text="Id do campus (o de GET /api/campi/).",
    )
    refeicao = serializers.CharField(
        help_text='Um de "cafe", "almoco" ou "jantar".',
    )
    data = serializers.DateField(
        help_text="Dia exibido. Pode diferir do pedido (RN05).",
    )
    refeicaoEncerrada = serializers.BooleanField()
    status = serializers.CharField(
        help_text='"publicado" ou "nao_publicado" (RF18).',
    )
    avisoSujeitoAAlteracao = serializers.CharField()
    alergenosIndisponivel = serializers.BooleanField()
    filtroMarcadorDesativado = serializers.BooleanField()
    categorias = CategoriaFiltradaSerializer(many=True)
