"""Teste 6 do guia: acesso às rotas do contrato (BE-03, 3.1 e 4.2).

Rota logada sem sessão -> 401 com `nao_autenticado`.
Rota pública sem sessão -> chega na view (que ainda responde 501).
Chamar todas as views também cobre os `return Response(501)` (CI exige 70%).
"""

import pytest
from rest_framework.test import APIClient

ROTAS_LOGADAS = [
    ("/api/sessao/", "get"),
    ("/api/sessao/", "delete"),
    ("/api/privacidade/aceite/", "post"),
    ("/api/avaliacoes/", "post"),
    ("/api/checkins/", "post"),
    ("/api/gamificacao/progresso/", "get"),
    ("/api/gamificacao/adesao/", "post"),
    ("/api/gamificacao/adesao/", "delete"),
]

ROTAS_PUBLICAS = [
    ("/api/cadastro/", "post"),
    ("/api/confirmar-email/abc123/", "post"),
    ("/api/reenviar-confirmacao/", "post"),
    ("/api/sessao/", "post"),
    ("/api/campi/", "get"),
    ("/api/cardapio/", "get"),
    ("/api/refeicoes/1/avaliacoes/", "get"),
    ("/api/avaliacoes/resumo/", "get"),
    ("/api/fila/previsao/", "get"),
    ("/api/ranking/1/", "get"),
]


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_LOGADAS)
def test_rota_logada_sem_sessao_da_401(rota, metodo):
    resposta = getattr(APIClient(), metodo)(rota)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


@pytest.mark.parametrize(("rota", "metodo"), ROTAS_PUBLICAS)
def test_rota_publica_responde_sem_login(rota, metodo):
    resposta = getattr(APIClient(), metodo)(rota)

    assert resposta.status_code == 501
