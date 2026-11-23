"""Pedidos dos usuários simulados no teste de carga (BD-14, #184).

Os dois endpoints do RNF01, sem login, como o PWA na tela do campus:
`GET /api/cardapio/?campus=` (o dia corrente) e
`GET /api/fila/previsao/?campus=&refeicao=` (hoje). Cada endpoint tem um nome
só, para o Locust somar os campi numa linha das estatísticas.
"""

from dataclasses import dataclass

NOME_CARDAPIO = "GET /api/cardapio/"
NOME_PREVISAO = "GET /api/fila/previsao/"
REFEICOES = ("cafe", "almoco", "jantar")

# O cardápio é a tela de entrada do PWA; a previsão é aberta menos vezes.
PESO_CARDAPIO = 3
PESO_PREVISAO = 1


@dataclass(frozen=True)
class Pedido:
    nome: str
    url: str


def pedidos_de_cardapio(campi: list[int]) -> list[Pedido]:
    return [Pedido(NOME_CARDAPIO, f"/api/cardapio/?campus={c}") for c in campi]


def pedidos_de_previsao(campi: list[int]) -> list[Pedido]:
    return [
        Pedido(NOME_PREVISAO, f"/api/fila/previsao/?campus={c}&refeicao={r}")
        for c in campi
        for r in REFEICOES
    ]


def pedidos(campi: list[int]) -> list[Pedido]:
    return pedidos_de_cardapio(campi) + pedidos_de_previsao(campi)
