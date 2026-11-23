"""Usuários simulados do teste de carga (BD-14, #184), para o Locust.

    locust -f carga/locustfile.py --headless --host http://127.0.0.1:8000 \\
        -u 2000 -r 50 -t 5m --csv resultado/carga

Cada usuário abre a tela do campus e fica nela: pede o cardápio ou a
previsão (pesos do `cenario`, 3 para 1) e espera de 3 a 7 s antes do próximo pedido, o tempo de
ler a tela (CARGA_ESPERA_MIN e CARGA_ESPERA_MAX trocam esse intervalo). Os
pedidos vêm de `carga.cenario`, que tem os testes.
"""

import os
import random

from locust import HttpUser, between, task

from carga.cenario import (
    PESO_CARDAPIO,
    PESO_PREVISAO,
    pedidos_de_cardapio,
    pedidos_de_previsao,
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
        self.client.get(pedido.url, name=pedido.nome)

    @task(PESO_CARDAPIO)
    def cardapio(self):
        self._pedir(CARDAPIO)

    @task(PESO_PREVISAO)
    def previsao(self):
        self._pedir(PREVISAO)
