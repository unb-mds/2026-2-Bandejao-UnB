"""Autenticação por sessão que responde 401 (e não 403) sem login (BE-03, 4.1)."""

import logging

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class CsrfInvalido(PermissionDenied):
    """403 de CSRF com código próprio (#112).

    Os outros 403 do contrato (`aviso_privacidade_pendente`,
    `conta_nao_confirmada`) têm outro significado: o front decide pelo código.
    O motivo exato (cookie ausente, token errado, origem que não confere) vai
    para o log deste módulo, e não para a resposta (ver `enforce_csrf`).
    """

    default_code = "csrf_invalido"


class SessaoAutenticacao(SessionAuthentication):
    """SessionAuthentication + cabeçalho WWW-Authenticate.

    O DRF só responde 401 quando a primeira classe de autenticação informa
    `authenticate_header`. A SessionAuthentication original não informa, e
    por isso devolve 403. O resto (cookie HttpOnly, CSRF) não muda (ADR 0007).
    """

    def authenticate_header(self, request):
        return "Session"

    def enforce_csrf(self, request):
        try:
            super().enforce_csrf(request)
        except PermissionDenied as exc:
            # O CSRFCheck do DRF só devolve o motivo, sem registrar nada.
            # Sem request.path: em /api/confirmar-email/{token}/ ele leva o token.
            logger.warning("CSRF recusado em %s: %s", request.method, exc.detail)
            raise CsrfInvalido from exc


class CsrfObrigatorio(BasePermission):
    """Cobra o CSRF também de quem ainda não tem sessão (#112).

    A SessionAuthentication só confere o CSRF quando já existe usuário logado.
    Sem esta permissão, o login aceitaria requisição de outro site (login
    CSRF: a vítima entra na conta do atacante). Use junto com AllowAny nas
    escritas públicas: `permission_classes = (AllowAny, CsrfObrigatorio)`.
    O PWA pega o cookie `csrftoken` antes, em `GET /api/csrf/`.
    """

    def has_permission(self, request, view):
        # Métodos de leitura passam direto: o próprio CSRFCheck do Django os ignora.
        # Para quem já está logado, o CSRF já foi cobrado na autenticação e é
        # conferido de novo aqui. É proposital: a permissão não depende de
        # saber se a requisição tem sessão.
        SessaoAutenticacao().enforce_csrf(request)
        return True


class SessaoAutenticacaoScheme(OpenApiAuthenticationExtension):
    """Ensina o drf-spectacular a descrever a classe acima no contrato.

    Sem isto ele avisa "could not resolve authenticator" e o
    `--fail-on-warn` derruba a geração do openapi.yaml.
    """

    target_class = "apps.cadastro.autenticacao.SessaoAutenticacao"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
