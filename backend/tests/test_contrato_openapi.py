"""
Testes do contrato OpenAPI v1 (BE-03).

Analogia: o contrato é a planta do prédio. Estes testes são o fiscal da obra:
se alguém mexer num serializer e esquecer de regerar a planta, o CI reprova.
"""

import json
from pathlib import Path

import pytest
from django.core.management import call_command
from drf_spectacular.generators import SchemaGenerator

# Arquivo oficial do contrato (se mudar o caminho, mude aqui e no comando de geração)
CAMINHO_CONTRATO = Path(__file__).resolve().parent.parent / "openapi.yaml"

# Tabela 2 do guia: (rota no schema, método HTTP em minúsculo)
ENDPOINTS_V1 = [
    ("/api/cadastro/", "post"),
    ("/api/confirmar-email/{token}/", "post"),
    ("/api/reenviar-confirmacao/", "post"),
    ("/api/sessao/", "post"),
    ("/api/sessao/", "get"),
    ("/api/sessao/", "delete"),
    ("/api/privacidade/aceite/", "post"),
    ("/api/cardapio/", "get"),
    ("/api/campi/", "get"),
    ("/api/avaliacoes/", "post"),
    ("/api/refeicoes/{refeicaoId}/avaliacoes/", "get"),
    ("/api/avaliacoes/resumo/", "get"),
    ("/api/checkins/", "post"),
    ("/api/fila/previsao/", "get"),
    ("/api/gamificacao/progresso/", "get"),
    ("/api/gamificacao/adesao/", "post"),
    ("/api/gamificacao/adesao/", "delete"),
    ("/api/ranking/{campusId}/", "get"),
]

# Campos dos extras que NÃO podem aparecer na v1
CAMPOS_PROIBIDOS = [
    "distintivo",
    "bonusSemana",
    "perguntaDevidaEm",
    "esperaEstimadaMin",
    "raioDeteccaoMetros",
]


@pytest.fixture(scope="module")
def schema():
    """Gera o schema OpenAPI em memória, direto do código atual."""
    return SchemaGenerator().get_schema(request=None, public=True)


def test_contrato_do_repositorio_esta_atualizado(tmp_path):
    """Teste 1: o openapi.yaml commitado é idêntico ao gerado agora."""
    gerado = tmp_path / "gerado.yaml"
    call_command("spectacular", "--file", str(gerado), "--validate", "--fail-on-warn")
    assert CAMINHO_CONTRATO.exists(), "openapi.yaml não existe no repositório"
    assert gerado.read_text() == CAMINHO_CONTRATO.read_text(), (
        "Contrato desatualizado: rode "
        "`python manage.py spectacular --validate --fail-on-warn --file openapi.yaml`"
    )


@pytest.mark.parametrize("rota, metodo", ENDPOINTS_V1)
def test_endpoint_existe_no_contrato(schema, rota, metodo):
    """Teste 2: cada endpoint da tabela 2 existe, com o método certo."""
    assert rota in schema["paths"], f"Rota ausente no contrato: {rota}"
    assert metodo in schema["paths"][rota], f"{metodo.upper()} ausente em {rota}"


def test_nenhum_campo_proibido_no_contrato(schema):
    """Teste 3: campos dos extras não vazam para a v1."""
    texto = json.dumps(schema)
    for campo in CAMPOS_PROIBIDOS:
        assert campo not in texto, f"Campo proibido no contrato: {campo}"


def test_contrato_tem_so_os_endpoints_da_v1(schema):
    """Endpoint fora da Tabela 2 (ex.: rascunho da v2) não entra sem aviso."""
    operacoes = {
        (rota, metodo)
        for rota, itens in schema["paths"].items()
        for metodo in itens
        if metodo in ("get", "post", "put", "patch", "delete")
    }
    assert operacoes == set(ENDPOINTS_V1)
