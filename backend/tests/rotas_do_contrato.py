"""Operações do contrato lidas do próprio schema (BE-03).

Os testes de acesso e de CSRF usam esta lista em vez de uma lista fixa:
um endpoint novo entra nos testes sozinho, sem ninguém lembrar de cadastrar.
"""

import re

from drf_spectacular.generators import SchemaGenerator

METODOS = ("get", "post", "put", "patch", "delete")
ESCRITAS = ("post", "put", "patch", "delete")


def operacoes_do_contrato():
    """Lista de (url de exemplo, método, pública?) de cada operação do schema.

    Parâmetros de rota ({token}, {campusId}...) viram "1", que serve tanto
    para <int:> quanto para <str:>.
    """
    schema = SchemaGenerator().get_schema(request=None, public=True)
    operacoes = []
    for rota, itens in schema["paths"].items():
        url = re.sub(r"\{\w+\}", "1", rota)
        for metodo, operacao in itens.items():
            if metodo in METODOS:
                publica = {} in operacao.get("security", [])
                operacoes.append((url, metodo, publica))
    return operacoes


OPERACOES = operacoes_do_contrato()
ROTAS_LOGADAS = [(url, metodo) for url, metodo, publica in OPERACOES if not publica]
ROTAS_PUBLICAS = [(url, metodo) for url, metodo, publica in OPERACOES if publica]
ESCRITAS_LOGADAS = [
    (url, metodo) for url, metodo in ROTAS_LOGADAS if metodo in ESCRITAS
]
