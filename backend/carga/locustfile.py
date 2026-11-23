"""Usuários simulados do teste de carga (BD-14, #184), para o Locust.

    locust -f carga/locustfile.py --headless --host http://127.0.0.1:8000 \
        -u 2000 -r 50 -t 5m --csv resultado/carga

Cada usuário faz um pedido, espera de 3 a 7 s (o tempo de ler a tela) e faz
o próximo, sorteando a cada pedido o campus e, na previsão, a refeição. O
cardápio pesa 3 e a previsão 1 (pesos do `cenario`). CARGA_ESPERA_MIN e
CARGA_ESPERA_MAX trocam o intervalo.

Uma resposta 200 sem o conteúdo completo (`nao_publicado`,
`dados_insuficientes`) conta como falha: é mais barata e derrubaria o p95.
Os pedidos e essa conferência vêm de `carga.cenario`, que tem os testes.
"""

import os
import random

from locust import HttpUser, between, task

from carga.cenario import (
    PESO_CARDAPIO,
    PESO_PREVISAO,
    pedidos_de_cardapio,
    pedidos_de_previsao,
    resposta_valida,
)

CAMPI = [int(c) for c in os.environ.get("CARGA_CAMPI", "1,2,3,4,5").split(",")]
ESPERA_MIN = float(os.environ.get("CARGA_ESPERA_MIN", "3"))
ESPERA_MAX = float(os.environ.get("CARGA_ESPERA_MAX", "7"))

CARDAPIO = pedidos_de_cardapio(CAMPI)
PREVISAO = pedidos_de_previsao(CAMPI)


class UsuarioDoPwa(HttpUser):
    wait_time = between(ESPERA_MIN, ESPERA_MAX)

    def _pedir(self, opcoes):
        pedido = random.choice(opcoes)
        with self.client.get(
            pedido.url, name=pedido.nome, catch_response=True
        ) as resposta:
            if resposta.status_code != 200:
                resposta.failure(f"HTTP {resposta.status_code}")
                return
            try:
                corpo = resposta.json()
            except ValueError:
                corpo = None
            if not resposta_valida(pedido.nome, corpo):
                resposta.failure("resposta sem o conteúdo completo")

    @task(PESO_CARDAPIO)
    def cardapio(self):
        self._pedir(CARDAPIO)

    @task(PESO_PREVISAO)
    def previsao(self):
        self._pedir(PREVISAO)
