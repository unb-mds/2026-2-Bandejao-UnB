"""Regras transversais do contrato OpenAPI (BE-03).

Teste 4: nenhuma resposta pública expõe dado pessoal (ADR 0008, RI10, RI12).
Teste 5: todo erro 4xx usa um componente com `codigo` obrigatório.
Extras: coordenadas nunca saem em resposta; rota logada declara o 401.
"""

import pytest

from tests.rotas_do_contrato import eh_publica, gerar_schema, operacoes

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

# Campos que cada resposta pública pode ter (em minúsculas, todos os status).
# Campo novo numa resposta pública só entra depois de uma decisão consciente:
# o teste falha até alguém acrescentá-lo aqui.
# Limitação: os nomes são comparados sem o caminho (em qual objeto o campo
# está). Um objeto aninhado novo com `nome` passa onde `nome` já é permitido.
_ERRO = {"codigo", "mensagem"}
CAMPOS_PUBLICOS_PERMITIDOS = {
    ("/api/cadastro/", "post"): _ERRO
    | {"status", "emailinstitucional", "apelidosugerido"},
    ("/api/confirmar-email/{token}/", "post"): _ERRO,
    ("/api/reenviar-confirmacao/", "post"): _ERRO,
    ("/api/sessao/", "post"): _ERRO | {"apelido", "tipo", "avisoprivacidadependente"},
    ("/api/campi/", "get"): {"id", "nome"},
    ("/api/cardapio/", "get"): _ERRO
    | {
        "alergenosindisponivel",
        "avisosujeitoaalteracao",
        "campus",
        "categorias",
        "contemmarcadorselecionado",
        "data",
        "descricao",
        "filtromarcadordesativado",
        "marcadores",
        "nome",
        "pratos",
        "refeicao",
        "refeicaoencerrada",
        "semopcaocompativel",
        "status",
    },
    ("/api/refeicoes/{refeicaoId}/avaliacoes/", "get"): _ERRO
    | {
        "resumoavaliacoes",
        "media",
        "quantidade",
        "comentarios",
        "apelido",
        "nota",
        "comentario",
        "criadaem",
    },
    ("/api/avaliacoes/resumo/", "get"): _ERRO
    | {"refeicaoid", "tipo", "media", "quantidade"},
    ("/api/fila/previsao/", "get"): _ERRO
    | {
        "status",
        "campus",
        "data",
        "tiporefeicao",
        "faixas",
        "inicio",
        "fim",
        "nivel",
        "ehpico",
    },
    ("/api/ranking/{campusId}/", "get"): _ERRO
    | {"campusid", "semestre", "linhas", "posicao", "apelido", "patente"},
}

# Coordenadas só existem no corpo do POST /api/checkins/ (RI09, RF12).
# Palavras longas: por substring (pega `latitudeAtual`).
PALAVRAS_DE_LOCALIZACAO = ("latitude", "longitude", "coordenadas", "localizacao")
# Abreviações: por igualdade, para `relatorio`, `colonia` e `geografia` não
# darem falso positivo. `userLat` escapa daqui, mas numa resposta pública
# CAMPOS_PUBLICOS_PERMITIDOS pega.
NOMES_DE_LOCALIZACAO = {"lat", "lng", "lon", "geo"}

# Exceções conscientes: (rota, método) -> campos permitidos na resposta.
# O cadastro devolve ao próprio solicitante o e-mail que ele acabou de enviar.
EXCECOES_PESSOAIS = {
    ("/api/cadastro/", "post"): {"emailinstitucional"},
}


@pytest.fixture(scope="module")
def schema():
    return gerar_schema()


def _eh_localizacao(nome):
    return nome in NOMES_DE_LOCALIZACAO or any(
        palavra in nome for palavra in PALAVRAS_DE_LOCALIZACAO
    )


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
    publicas = [r for r, m, o in operacoes(schema) if eh_publica(o)]
    assert len(publicas) >= 6


def test_resposta_publica_nao_expoe_dado_pessoal(schema):
    """Teste 4: nenhuma operação pública, em nenhum status, expõe dado pessoal."""
    violacoes = []
    for rota, metodo, operacao in operacoes(schema):
        if not eh_publica(operacao):
            continue
        permitidos = EXCECOES_PESSOAIS.get((rota, metodo), set())
        for nome in _campos_das_respostas(schema, operacao) - permitidos:
            if any(palavra in nome for palavra in PALAVRAS_PESSOAIS):
                violacoes.append(f"{metodo.upper()} {rota}: {nome}")
    assert not violacoes, f"respostas públicas com dado pessoal: {violacoes}"


def test_coordenadas_nunca_saem_em_resposta(schema):
    """Latitude e longitude só entram (corpo do check-in); nunca saem (RI09)."""
    violacoes = []
    for rota, metodo, operacao in operacoes(schema):
        for nome in _campos_das_respostas(schema, operacao):
            if _eh_localizacao(nome):
                violacoes.append(f"{metodo.upper()} {rota}: {nome}")
        for parametro in operacao.get("parameters", []):
            nome = parametro["name"].lower()
            if _eh_localizacao(nome):
                violacoes.append(f"{metodo.upper()} {rota}: parâmetro {nome}")
    assert not violacoes, f"localização fora do corpo de entrada: {violacoes}"


def test_todo_erro_4xx_usa_componente_com_codigo(schema):
    """Teste 5: todo 4xx devolve um componente com `codigo` declarado e obrigatório."""
    sem_codigo = []
    for rota, metodo, operacao in operacoes(schema):
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
        for rota, metodo, operacao in operacoes(schema)
        if not eh_publica(operacao) and "401" not in operacao["responses"]
    ]
    assert not sem_401, f"rotas logadas sem 401 declarado: {sem_401}"


def test_resposta_publica_so_tem_campos_permitidos(schema):
    """Lista positiva: pega `nome`, `userId`, `lat`... que a lista de palavras deixa passar.

    Compara nomes, não caminhos (veja a limitação em CAMPOS_PUBLICOS_PERMITIDOS).
    """
    publicas = {(r, m): o for r, m, o in operacoes(schema) if eh_publica(o)}
    assert set(publicas) == set(CAMPOS_PUBLICOS_PERMITIDOS), (
        "rota pública nova ou removida"
    )

    extras = []
    for (rota, metodo), operacao in publicas.items():
        permitidos = CAMPOS_PUBLICOS_PERMITIDOS[(rota, metodo)]
        for nome in _campos_das_respostas(schema, operacao) - permitidos:
            extras.append(f"{metodo.upper()} {rota}: {nome}")
    assert not extras, f"campos novos em respostas públicas: {extras}"
