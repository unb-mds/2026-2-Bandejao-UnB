"""Endpoints do app avaliacao (entram nas histórias de usuário)."""

from django.urls import path

from apps.avaliacao.views import (
    AvaliacaoView,
    RefeicaoAvaliacoesView,
    ResumoDoDiaView,
)

app_name = "avaliacao"

urlpatterns = [
    path("avaliacoes/", AvaliacaoView.as_view(), name="avaliacao"),
    path("avaliacoes/resumo/", ResumoDoDiaView.as_view(), name="resumo-do-dia"),
    path(
        "refeicoes/<int:refeicaoId>/avaliacoes/",
        RefeicaoAvaliacoesView.as_view(),
        name="refeicao-avaliacoes",
    ),
]
