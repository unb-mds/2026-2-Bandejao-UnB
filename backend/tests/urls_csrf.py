"""URLs só dos testes de segurança da sessão (ADR 0007).

Usadas com @pytest.mark.urls("tests.urls_csrf"). Não fazem parte da API real:
existem para exercitar o CsrfViewMiddleware, a SessionAuthentication do DRF e
os cookies emitidos, sem depender de endpoints que ainda não existem (BE-05).
"""

from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class EscritaView(APIView):
    """Usa só os padrões do DRF (autenticada, com sessão e CSRF)."""

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"ok": True})

    def post(self, request):
        return Response({"ok": True})


class SemPermissaoView(APIView):
    """De propósito sem permission_classes: vale o padrão do settings."""

    def get(self, request):
        return Response({"ok": True})


class LoginView(APIView):
    """Faz login de verdade para o teste conferir os cookies emitidos."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request):
        usuario = authenticate(
            request,
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if usuario is None:
            return Response({"ok": False}, status=401)
        login(request, usuario)
        return Response({"ok": True})


def escrita_django_pura(request):
    """View Django comum (sem DRF): só o CsrfViewMiddleware a protege.

    A SessionAuthentication do DRF faz a própria checagem de CSRF e as
    APIView são isentas para o middleware. Sem esta view, remover o
    CsrfViewMiddleware do settings não quebraria nenhum teste.
    """
    return JsonResponse({"ok": True})


urlpatterns = [
    path("teste/escrita-django/", escrita_django_pura),
    path("teste/escrita/", EscritaView.as_view()),
    path("teste/sem-permissao/", SemPermissaoView.as_view()),
    path("teste/login/", LoginView.as_view()),
]
