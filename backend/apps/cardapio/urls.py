"""Endpoints do app cardapio."""

from django.urls import path

from apps.cardapio.views import CampiView, CardapioView

app_name = "cardapio"

urlpatterns = [
    # Filtros por query string (X4), nunca /api/cardapio/{campus}/{semana}/
    path("cardapio/", CardapioView.as_view(), name="cardapio"),
    path("campi/", CampiView.as_view(), name="campi"),
]
