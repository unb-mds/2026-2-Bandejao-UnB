"""Autenticação por sessão que responde 401 (e não 403) sem login (BE-03, 4.1)."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import SessionAuthentication


class SessaoAutenticacao(SessionAuthentication):
    """SessionAuthentication + cabeçalho WWW-Authenticate.

    O DRF só responde 401 quando a primeira classe de autenticação informa
    `authenticate_header`. A SessionAuthentication original não informa, e
    por isso devolve 403. O resto (cookie HttpOnly, CSRF) não muda (ADR 0007).
    """

    def authenticate_header(self, request):
        return "Session"


class SessaoAutenticacaoScheme(OpenApiAuthenticationExtension):
    """Ensina o drf-spectacular a descrever a classe acima no contrato.

    Sem isto ele avisa "could not resolve authenticator" e o
    `--fail-on-warn` derruba a geração do openapi.yaml.
    """

    target_class = "apps.cadastro.autenticacao.SessaoAutenticacao"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
