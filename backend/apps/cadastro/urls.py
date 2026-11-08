"""Endpoints do app cadastro."""

from django.urls import path

from apps.cadastro.views import (
    AceiteAvisoPrivacidadeView,
    CadastroView,
    ConfirmacaoEmailView,
    ReenvioConfirmacaoView,
    SessaoView,
)

app_name = "cadastro"

urlpatterns = [
    path("cadastro/", CadastroView.as_view(), name="cadastro"),
    # <str:token>: o token do link enviado por e-mail
    path(
        "confirmar-email/<str:token>/",
        ConfirmacaoEmailView.as_view(),
        name="confirmar-email",
    ),
    path(
        "reenviar-confirmacao/",
        ReenvioConfirmacaoView.as_view(),
        name="reenviar-confirmacao",
    ),
    # Uma rota, três verbos: POST (login), GET (quem sou eu), DELETE (logout)
    path("sessao/", SessaoView.as_view(), name="sessao"),
    path(
        "privacidade/aceite/",
        AceiteAvisoPrivacidadeView.as_view(),
        name="privacidade-aceite",
    ),
]
