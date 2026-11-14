"""Formato de erro do contrato da API (BE-03).

Toda resposta de erro declarada no contrato traz `codigo` (obrigatório) e
`mensagem`. O handler de `config/excecoes.py` aplica o formato aos erros de
mensagem única (401, 403 de CSRF e exceções com código próprio). O 400 de
validação, o 404, o 405 e o 415 ainda saem como o DRF devolve. Também não
existe um objeto `campos` para os erros de validação.
"""

from rest_framework import serializers

ESCRITAS = ("post", "put", "patch", "delete")
DESCRICAO_CSRF = (
    "Token CSRF ausente ou inválido: pegue o cookie em `GET /api/csrf/` e "
    "mande o valor no cabeçalho `X-CSRFToken`. `codigo`: `csrf_invalido`."
)


class ErroSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Código do erro, em snake_case.")
    mensagem = serializers.CharField(help_text="Texto para mostrar ao usuário.")


def documentar_csrf_invalido(result, generator, request, public):
    """Hook do drf-spectacular: o 403 `csrf_invalido` em toda escrita (#112).

    Escrever o 403 view a view seria fácil de esquecer numa rota nova. Onde a
    rota já tem um 403 (ex.: `aviso_privacidade_pendente`), a descrição ganha
    o caso do CSRF, sem trocar o que já estava lá.
    """
    for itens in result["paths"].values():
        for metodo, operacao in itens.items():
            if metodo not in ESCRITAS:
                continue
            respostas = operacao["responses"]
            if "403" in respostas:
                anterior = respostas["403"]["description"]
                respostas["403"]["description"] = f"{anterior} Ou: {DESCRICAO_CSRF}"
            else:
                respostas["403"] = {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Erro"}
                        }
                    },
                    "description": DESCRICAO_CSRF,
                }
    return result
