"""Operações do contrato lidas do próprio schema (BE-03).

Os testes de acesso e de CSRF usam esta lista em vez de uma lista fixa:
um endpoint novo entra nos testes sozinho, sem ninguém lembrar de cadastrar.
Os testes do contrato também usam daqui o schema, `operacoes` e `eh_publica`,
para a regra de "rota pública" ficar num lugar só.
"""

import re
from functools import cache

from drf_spectacular.generators import SchemaGenerator

METODOS = ("get", "post", "put", "patch", "delete")
ESCRITAS = ("post", "put", "patch", "delete")


@cache
def gerar_schema():
    """Schema OpenAPI em memória, direto do código atual (gerado uma vez só)."""
    return SchemaGenerator().get_schema(request=None, public=True)


def operacoes(schema):
    """Percorre todas as operações como (rota, método, operação)."""
    for rota, itens in schema["paths"].items():
        for metodo, operacao in itens.items():
            if metodo in METODOS:
                yield rota, metodo, operacao


def eh_publica(operacao):
    """Operação pública: o schema aceita requisição sem credencial (`{}`)."""
    return {} in operacao.get("security", [])


def operacoes_do_contrato():
    """Lista de (url de exemplo, método, pública?) de cada operação do schema.

    Parâmetros de rota ({token}, {campusId}...) viram "1", que serve tanto
    para <int:> quanto para <str:>.
    """
    return [
        (re.sub(r"\{\w+\}", "1", rota), metodo, eh_publica(operacao))
        for rota, metodo, operacao in operacoes(gerar_schema())
    ]


OPERACOES = operacoes_do_contrato()
ROTAS_LOGADAS = [(url, metodo) for url, metodo, publica in OPERACOES if not publica]
ROTAS_PUBLICAS = [(url, metodo) for url, metodo, publica in OPERACOES if publica]
ESCRITAS_LOGADAS = [
    (url, metodo) for url, metodo in ROTAS_LOGADAS if metodo in ESCRITAS
]
