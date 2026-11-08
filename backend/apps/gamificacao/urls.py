"""Endpoints do app gamificacao (entram nas histórias de usuário)."""

from django.urls import path

from apps.gamificacao.views import ProgressoView, RankingAdesaoView, RankingView

app_name = "gamificacao"

urlpatterns = [
    path("gamificacao/progresso/", ProgressoView.as_view(), name="progresso"),
    path("gamificacao/adesao/", RankingAdesaoView.as_view(), name="adesao"),
    path("ranking/<int:campusId>/", RankingView.as_view(), name="ranking"),
]
