"""Formato de erro do contrato da API (BE-03).

Toda resposta de erro declarada no contrato traz `codigo` (obrigatório) e
`mensagem`. Por enquanto, só o 401 `nao_autenticado` é aplicado de fato, pelo
handler de `config/excecoes.py`. O handler que leva este formato a todos os
4xx (400 de validação, 403 de CSRF, 404, 405, 415) entra na BE-05. Também não
existe um objeto `campos` para os erros de validação.
"""

from rest_framework import serializers


class ErroSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Código do erro, em snake_case.")
    mensagem = serializers.CharField(help_text="Texto para mostrar ao usuário.")
