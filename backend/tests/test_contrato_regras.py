"""Testes 4 e 5 do guia BE-03 (3.1): dados pessoais e formato de erro."""

import pytest
from drf_spectacular.generators import SchemaGenerator

# Respostas públicas que nunca podem expor dado pessoal (ADR 0008, RI10, RI12).
ROTAS_PUBLICAS_SENSIVEIS = [
    ("/api/ranking/{campusId}/", "get"),
    ("/api/refeicoes/{refeicaoId}/avaliacoes/", "get"),
]
PALAVRAS_PESSOAIS = ("pontos", "email", "matricula")


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def _resolver(schema, no):
    """Troca um {"$ref": ...} pelo componente a que ele aponta."""
    ref = no.get("$ref")
    if ref is None:
        return no
    return schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def _nomes_de_campos(schema, no, vistos=None):
    """Todos os nomes de campo alcançáveis a partir de um nó do schema."""
    vistos = set() if vistos is None else vistos
    if "$ref" in no:
        if no["$ref"] in vistos:
            return set()
        vistos.add(no["$ref"])
        no = _resolver(schema, no)
    nomes = set()
    for nome, filho in no.get("properties", {}).items():
        nomes.add(nome)
        nomes |= _nomes_de_campos(schema, filho, vistos)
    if "items" in no:
        nomes |= _nomes_de_campos(schema, no["items"], vistos)
    for parte in no.get("allOf", []):
        nomes |= _nomes_de_campos(schema, parte, vistos)
    return nomes


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_PUBLICAS_SENSIVEIS)
def test_resposta_publica_nao_expoe_dado_pessoal(schema, rota, metodo):
    """Teste 4: nada de pontos, e-mail ou matrícula/SIAPE."""
    resposta = schema["paths"][rota][metodo]["responses"]["200"]
    corpo = resposta["content"]["application/json"]["schema"]

    nomes = {n.lower() for n in _nomes_de_campos(schema, corpo)}

    achados = {n for n in nomes if any(p in n for p in PALAVRAS_PESSOAIS)}
    assert not achados, f"{metodo.upper()} {rota} expõe {sorted(achados)}"


def test_todo_erro_4xx_usa_componente_com_codigo(schema):
    """Teste 5: toda resposta 4xx devolve um componente com `codigo` obrigatório."""
    sem_codigo = []
    for rota, operacoes in schema["paths"].items():
        for metodo, operacao in operacoes.items():
            for status, resposta in operacao["responses"].items():
                if not status.startswith("4"):
                    continue
                corpo = resposta.get("content", {}).get("application/json", {})
                componente = _resolver(schema, corpo.get("schema", {}))
                if "codigo" not in componente.get("required", []):
                    sem_codigo.append(f"{metodo.upper()} {rota} {status}")
    assert not sem_codigo, f"4xx sem `codigo` obrigatório: {sem_codigo}"
