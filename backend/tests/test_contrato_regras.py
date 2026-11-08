"""Regras transversais do contrato OpenAPI (BE-03).

Teste 4: nenhuma resposta pública expõe dado pessoal (ADR 0008, RI10, RI12).
Teste 5: todo erro 4xx usa um componente com `codigo` obrigatório.
Extras: coordenadas nunca saem em resposta; rota logada declara o 401.
"""

import pytest
from drf_spectacular.generators import SchemaGenerator

METODOS = ("get", "post", "put", "patch", "delete")

# Nomes (em minúsculas) que nunca podem aparecer numa resposta pública.
PALAVRAS_PESSOAIS = (
    "pontos",
    "email",
    "matricula",
    "siape",
    "senha",
    "password",
    "nomecompleto",
    "usuario",
    "cpf",
    "telefone",
)

# Coordenadas só existem no corpo do POST /api/checkins/ (RI09, RF12).
PALAVRAS_DE_LOCALIZACAO = ("latitude", "longitude", "coordenadas")

# Exceções conscientes: (rota, método) -> campos permitidos na resposta.
# O cadastro devolve ao próprio solicitante o e-mail que ele acabou de enviar.
EXCECOES_PESSOAIS = {
    ("/api/cadastro/", "post"): {"emailinstitucional"},
}


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def _operacoes(schema):
    """Percorre todas as operações como (rota, método, operação)."""
    for rota, itens in schema["paths"].items():
        for metodo, operacao in itens.items():
            if metodo in METODOS:
                yield rota, metodo, operacao


def _eh_publica(operacao):
    """Operação pública: o schema aceita requisição sem credencial (`{}`)."""
    return {} in operacao.get("security", [])


def _componente(schema, no):
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
        no = _componente(schema, no)
    nomes = set()
    for nome, filho in no.get("properties", {}).items():
        nomes.add(nome)
        nomes |= _nomes_de_campos(schema, filho, vistos)
    filhos = [no.get("items"), no.get("additionalProperties")]
    filhos += no.get("allOf", []) + no.get("oneOf", []) + no.get("anyOf", [])
    for filho in filhos:
        if isinstance(filho, dict):
            nomes |= _nomes_de_campos(schema, filho, vistos)
    return nomes


def _campos_das_respostas(schema, operacao):
    """Nomes de campo de todas as respostas (qualquer status) da operação."""
    nomes = set()
    for resposta in operacao["responses"].values():
        corpo = resposta.get("content", {}).get("application/json", {})
        if "schema" in corpo:
            nomes |= {n.lower() for n in _nomes_de_campos(schema, corpo["schema"])}
    return nomes


def test_ha_operacoes_publicas_no_schema(schema):
    """Guarda: se a descoberta de rotas públicas quebrar, o teste 4 não vira vazio."""
    publicas = [r for r, m, o in _operacoes(schema) if _eh_publica(o)]
    assert len(publicas) >= 6


def test_resposta_publica_nao_expoe_dado_pessoal(schema):
    """Teste 4: nenhuma operação pública, em nenhum status, expõe dado pessoal."""
    violacoes = []
    for rota, metodo, operacao in _operacoes(schema):
        if not _eh_publica(operacao):
            continue
        permitidos = EXCECOES_PESSOAIS.get((rota, metodo), set())
        for nome in _campos_das_respostas(schema, operacao) - permitidos:
            if any(palavra in nome for palavra in PALAVRAS_PESSOAIS):
                violacoes.append(f"{metodo.upper()} {rota}: {nome}")
    assert not violacoes, f"respostas públicas com dado pessoal: {violacoes}"


def test_coordenadas_nunca_saem_em_resposta(schema):
    """Latitude e longitude só entram (corpo do check-in); nunca saem (RI09)."""
    violacoes = []
    for rota, metodo, operacao in _operacoes(schema):
        for nome in _campos_das_respostas(schema, operacao):
            if any(palavra in nome for palavra in PALAVRAS_DE_LOCALIZACAO):
                violacoes.append(f"{metodo.upper()} {rota}: {nome}")
        for parametro in operacao.get("parameters", []):
            nome = parametro["name"].lower()
            if any(palavra in nome for palavra in PALAVRAS_DE_LOCALIZACAO):
                violacoes.append(f"{metodo.upper()} {rota}: parâmetro {nome}")
    assert not violacoes, f"localização fora do corpo de entrada: {violacoes}"


def test_todo_erro_4xx_usa_componente_com_codigo(schema):
    """Teste 5: todo 4xx devolve um componente com `codigo` declarado e obrigatório."""
    sem_codigo = []
    for rota, metodo, operacao in _operacoes(schema):
        for status, resposta in operacao["responses"].items():
            if not status.startswith("4"):
                continue
            corpo = resposta.get("content", {}).get("application/json", {})
            componente = _componente(schema, corpo.get("schema", {}))
            declarado = "codigo" in componente.get("properties", {})
            obrigatorio = "codigo" in componente.get("required", [])
            if not (declarado and obrigatorio):
                sem_codigo.append(f"{metodo.upper()} {rota} {status}")
    assert not sem_codigo, f"4xx sem `codigo` obrigatório: {sem_codigo}"


def test_toda_operacao_logada_declara_o_401(schema):
    """Rota logada sem sessão responde 401 (guia 4.1): o contrato precisa dizer isso."""
    sem_401 = [
        f"{metodo.upper()} {rota}"
        for rota, metodo, operacao in _operacoes(schema)
        if not _eh_publica(operacao) and "401" not in operacao["responses"]
    ]
    assert not sem_401, f"rotas logadas sem 401 declarado: {sem_401}"
