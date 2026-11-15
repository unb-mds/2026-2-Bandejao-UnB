"""Formato de erro `{codigo, mensagem}` do tratador de exceções (#112).

O front decide pelo `codigo`, nunca só pelo status: 401 de "sem sessão" e de
"senha errada" precisam de códigos diferentes, e o 403 de CSRF não pode se
confundir com os outros 403 do contrato.
"""

import logging

import pytest
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.test import APIClient

from apps.cadastro.autenticacao import CsrfInvalido
from config.excecoes import tratador_de_excecoes


def _tratar(exc):
    return tratador_de_excecoes(exc, context={})


def test_sem_sessao_vira_nao_autenticado():
    resposta = _tratar(NotAuthenticated())

    assert resposta.status_code == 401
    assert resposta.data["codigo"] == "nao_autenticado"
    assert resposta.data["mensagem"]


def test_not_authenticated_com_codigo_proprio_nao_e_sobrescrito():
    resposta = _tratar(NotAuthenticated("Sessão encerrada.", code="sessao_encerrada"))

    assert resposta.status_code == 401
    assert resposta.data == {
        "codigo": "sessao_encerrada",
        "mensagem": "Sessão encerrada.",
    }


def test_authentication_failed_vira_credenciais_invalidas():
    """Sem isso, "senha errada" chegaria ao front sem `codigo` (RF03.1)."""
    resposta = _tratar(AuthenticationFailed())

    assert resposta.status_code == 401
    assert resposta.data["codigo"] == "credenciais_invalidas"
    assert resposta.data["mensagem"]


def test_authentication_failed_com_codigo_proprio_usa_esse_codigo():
    resposta = _tratar(
        AuthenticationFailed("Tente de novo em 10 minutos.", code="login_bloqueado")
    )

    assert resposta.data == {
        "codigo": "login_bloqueado",
        "mensagem": "Tente de novo em 10 minutos.",
    }


def test_csrf_vira_csrf_invalido():
    resposta = _tratar(CsrfInvalido())

    assert resposta.status_code == 403
    assert resposta.data["codigo"] == "csrf_invalido"
    assert resposta.data["mensagem"]


def test_permission_denied_com_codigo_proprio_usa_esse_codigo():
    """Caminho das views: `raise PermissionDenied(msg, code="conta_nao_confirmada")`."""
    resposta = _tratar(
        PermissionDenied("Confirme seu e-mail.", code="conta_nao_confirmada")
    )

    assert resposta.status_code == 403
    assert resposta.data == {
        "codigo": "conta_nao_confirmada",
        "mensagem": "Confirme seu e-mail.",
    }


def test_excecao_que_nao_e_do_drf_segue_para_o_django():
    assert _tratar(ValueError("erro")) is None


@pytest.mark.parametrize(
    ("exc", "status"),
    [
        (ValidationError({"senha": ["Muito curta."]}), 400),
        (ValidationError("Mensagem única."), 400),
        (NotFound(), 404),
        (MethodNotAllowed("PUT"), 405),
        (PermissionDenied(), 403),
    ],
)
def test_erro_com_codigo_padrao_segue_como_o_drf_devolve(exc, status):
    """O formato do projeto só entra onde há tradução ou código próprio.

    O 422 de validação de cada rota é responsabilidade da view (BE-05).
    """
    resposta = _tratar(exc)

    assert resposta.status_code == status
    assert "codigo" not in resposta.data


@pytest.fixture
def log_de_requisicoes():
    """Anexa um coletor ao logger `django.request` (que não propaga)."""
    registros = []

    class Coletor(logging.Handler):
        def emit(self, record):
            registros.append(self.format(record))

    logger = logging.getLogger("django.request")
    coletor = Coletor()
    logger.addHandler(coletor)
    yield registros
    logger.removeHandler(coletor)


def test_erro_5xx_vai_para_o_log_em_producao(log_de_requisicoes):
    """Sem o LOGGING, com DEBUG=False um 5xx não aparece em lugar nenhum."""
    # As views ainda sem lógica respondem 501.
    APIClient().post("/api/cadastro/", {}, format="json")

    assert any("/api/cadastro/" in m for m in log_de_requisicoes)


def test_log_nao_mostra_o_token_da_confirmacao_de_email(log_de_requisicoes):
    """Quem lê o log não pode confirmar a conta de outra pessoa."""
    APIClient().post("/api/confirmar-email/token-secreto/", {}, format="json")

    assert log_de_requisicoes
    assert any("/api/confirmar-email/" in m for m in log_de_requisicoes)
    assert not any("token-secreto" in m for m in log_de_requisicoes)
