"""Formato de erro `{codigo, mensagem}` do tratador de exceções (#112).

O front decide pelo `codigo`, nunca só pelo status: 401 de "sem sessão" e de
"senha errada" precisam de códigos diferentes, e o 403 de CSRF não pode se
confundir com os outros 403 do contrato.
"""

import logging

from django.conf import settings
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)

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


def test_erro_500_vai_para_o_console_em_producao():
    """Sem isto, com DEBUG=False o traceback de um 500 não aparece em lugar nenhum."""
    assert settings.LOGGING["loggers"]["django.request"]["level"] == "ERROR"
    handlers = logging.getLogger("django.request").handlers
    console = [h for h in handlers if isinstance(h, logging.StreamHandler)]
    assert console
    # Sem o filtro require_debug_true do Django: vale também com DEBUG=False.
    assert all(not h.filters for h in console)
