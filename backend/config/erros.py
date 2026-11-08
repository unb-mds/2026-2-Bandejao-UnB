"""Formato de erro único da API: toda resposta 4xx tem `codigo` (BE-03)."""

from rest_framework import serializers


class ErroSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Código do erro, em snake_case.")
    mensagem = serializers.CharField(help_text="Texto para mostrar ao usuário.")
