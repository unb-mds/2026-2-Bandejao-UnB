"""POST /api/avaliacoes/ (BE-13, RF15.1, RI01, Avaliação N4 4a).

O cliente exige CSRF, como o navegador (#112).
"""

from datetime import timedelta
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.avaliacao.models import Avaliacao
from apps.avaliacao.tests.apoio import DURANTE_O_ALMOCO, SEGUNDA, TERCA
from apps.cardapio.models import TipoRefeicao
from apps.cardapio.tests.apoio_cardapio import criar_refeicao
from apps.gamificacao.pontuacao_service import PontuacaoService, ResultadoPontuacao
from tests.rotas_do_contrato import gerar_schema

ROTA = "/api/avaliacoes/"


def postar(cliente, dados, agora=DURANTE_O_ALMOCO):
    with mock.patch("django.utils.timezone.now", return_value=agora):
        return cliente.post(ROTA, dados, format="json")


def assert_erro(resposta, situacao, codigo):
    assert resposta.status_code == situacao
    assert set(resposta.json()) == {"codigo", "mensagem"}
    assert resposta.json()["codigo"] == codigo
    assert resposta.json()["mensagem"]


# --- 201 e 200 ---------------------------------------------------------------


def test_primeira_avaliacao_devolve_201_com_avaliacao_e_pontos(logado, almoco):
    resposta = postar(
        logado, {"refeicaoId": almoco.id, "nota": 5, "comentario": "Ótimo"}
    )

    assert resposta.status_code == 201
    avaliacao = Avaliacao.objects.get()
    assert resposta.json() == {
        "avaliacao": {
            "id": avaliacao.id,
            "refeicaoId": almoco.id,
            "nota": 5,
            "comentario": "Ótimo",
            "criadaEm": "2026-11-24T12:07:00-03:00",
            "editadaEm": None,
        },
        # Sem check-in nesta refeição, a avaliação ainda não pontua: os 5
        # pontos vêm quando o check-in for feito (RN09).
        "pontos": {"total": 0, "contribuicao": 0, "avaliacaoLiberada": 0},
    }


def test_comentario_e_opcional(logado, almoco):
    resposta = postar(logado, {"refeicaoId": almoco.id, "nota": 3})

    assert resposta.status_code == 201
    assert resposta.json()["avaliacao"]["comentario"] == ""
    assert Avaliacao.objects.get().comentario is None


def test_comentario_nulo_e_aceito(logado, almoco):
    resposta = postar(logado, {"refeicaoId": almoco.id, "nota": 3, "comentario": None})

    assert resposta.status_code == 201


def test_contrato_aceita_comentario_nulo():
    """O contrato diz o mesmo que a view (revisão do #230)."""
    entrada = gerar_schema()["components"]["schemas"]["AvaliacaoEntradaRequest"]

    assert entrada["properties"]["comentario"]["nullable"] is True


def test_avaliar_de_novo_devolve_200_e_edita(logado, almoco):
    postar(logado, {"refeicaoId": almoco.id, "nota": 2, "comentario": "Frio"})

    resposta = postar(
        logado,
        {"refeicaoId": almoco.id, "nota": 4},
        agora=DURANTE_O_ALMOCO + timedelta(hours=1),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()["avaliacao"]
    assert (corpo["nota"], corpo["comentario"]) == (4, "")
    assert corpo["criadaEm"] == "2026-11-24T12:07:00-03:00"
    assert corpo["editadaEm"] == "2026-11-24T13:07:00-03:00"
    assert Avaliacao.objects.count() == 1


def test_pontos_da_gamificacao_vao_na_resposta(logado, almoco):
    with mock.patch.object(
        PontuacaoService,
        "registrar_contribuicao",
        return_value=ResultadoPontuacao(contribuicao=5, avaliacao_liberada=3),
    ):
        resposta = postar(logado, {"refeicaoId": almoco.id, "nota": 4})

    assert resposta.json()["pontos"] == {
        "total": 8,
        "contribuicao": 5,
        "avaliacaoLiberada": 3,
    }


def test_avaliacao_e_da_conta_da_sessao(logado, conta, outra_conta, almoco):
    postar(
        logado,
        {"refeicaoId": almoco.id, "nota": 4, "usuario": outra_conta.id, "conta": 999},
    )

    assert Avaliacao.objects.get().usuario == conta


def test_campos_de_pontos_ou_de_campus_do_front_sao_ignorados(logado, almoco):
    """RN09: campus, refeição e pontos da pontuação nunca vêm do front."""
    with mock.patch.object(
        PontuacaoService, "registrar_contribuicao", return_value=ResultadoPontuacao()
    ) as pontuar:
        postar(
            logado,
            {
                "refeicaoId": almoco.id,
                "nota": 4,
                "campus": 999,
                "tipoRefeicao": "jantar",
                "pontos": 100,
            },
        )

    refeicao_ref = pontuar.call_args.args[3]
    assert (refeicao_ref.campus, refeicao_ref.tipo_refeicao) == (
        almoco.campus,
        "almoco",
    )


def test_resposta_nao_traz_matricula_nem_email(logado, conta, almoco):
    """Teste da ADR 0008 (RI10)."""
    resposta = postar(logado, {"refeicaoId": almoco.id, "nota": 4})

    conteudo = resposta.content.decode()
    assert conta.matricula_siape not in conteudo
    assert conta.email_institucional not in conteudo
    assert "@" not in conteudo


# --- 401 (RI01) --------------------------------------------------------------


def test_sem_sessao_da_401_sem_gravar(almoco):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)

    resposta = postar(cliente, {"refeicaoId": almoco.id, "nota": 4})

    assert_erro(resposta, 401, "nao_autenticado")
    assert not Avaliacao.objects.exists()


# --- 404 ---------------------------------------------------------------------


@pytest.mark.parametrize("refeicao_id", [999_999, 10**30])
def test_refeicao_inexistente_da_404(logado, almoco, refeicao_id):
    resposta = postar(logado, {"refeicaoId": refeicao_id, "nota": 4})

    assert_erro(resposta, 404, "refeicao_nao_encontrada")


# --- 422 ---------------------------------------------------------------------


def test_refeicao_de_outro_dia_da_422_com_o_motivo(logado, gama):
    segunda = criar_refeicao(gama, SEGUNDA)

    resposta = postar(logado, {"refeicaoId": segunda.id, "nota": 4})

    assert_erro(resposta, 422, "janela_avaliacao_fechada")
    assert "hoje" in resposta.json()["mensagem"]
    assert not Avaliacao.objects.exists()


def test_refeicao_que_ainda_nao_comecou_da_422_com_o_horario(logado, gama):
    jantar = criar_refeicao(gama, TERCA, TipoRefeicao.JANTAR)

    resposta = postar(logado, {"refeicaoId": jantar.id, "nota": 4})

    assert_erro(resposta, 422, "janela_avaliacao_fechada")
    assert resposta.json()["mensagem"] == (
        "A avaliação do jantar abre às 17h00, quando a refeição começa."
    )


@pytest.mark.parametrize("nota", [None, 0, 6, 4.5, "4", True])
def test_nota_invalida_da_422(logado, almoco, nota):
    resposta = postar(logado, {"refeicaoId": almoco.id, "nota": nota})

    assert_erro(resposta, 422, "nota_invalida")
    assert not Avaliacao.objects.exists()


def test_sem_nota_da_422(logado, almoco):
    resposta = postar(logado, {"refeicaoId": almoco.id})

    assert_erro(resposta, 422, "nota_invalida")


def test_comentario_com_mais_de_500_caracteres_da_422(logado, almoco):
    resposta = postar(
        logado, {"refeicaoId": almoco.id, "nota": 4, "comentario": "a" * 501}
    )

    assert_erro(resposta, 422, "comentario_muito_longo")
    assert not Avaliacao.objects.exists()


def test_comentario_com_500_caracteres_e_aceito(logado, almoco):
    resposta = postar(
        logado, {"refeicaoId": almoco.id, "nota": 4, "comentario": "a" * 500}
    )

    assert resposta.status_code == 201


# --- 400 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "dados",
    [
        {"nota": 4},
        {"refeicaoId": None, "nota": 4},
        {"refeicaoId": "1", "nota": 4},
        {"refeicaoId": True, "nota": 4},
        {"refeicaoId": 1.0, "nota": 4},
        {"refeicaoId": "ALMOCO", "nota": 4, "comentario": 123},
        {"refeicaoId": "ALMOCO", "nota": 4, "comentario": ["a"]},
        [1, 4],
    ],
)
def test_corpo_fora_do_formato_da_400(logado, almoco, dados):
    # Comentário errado numa refeição que existe e está aberta.
    if isinstance(dados, dict) and dados.get("refeicaoId") == "ALMOCO":
        dados = {**dados, "refeicaoId": almoco.id}

    resposta = postar(logado, dados)

    assert_erro(resposta, 400, "dados_invalidos")
    assert not Avaliacao.objects.exists()
