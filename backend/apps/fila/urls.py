"""Endpoints do app fila."""

from django.urls import path

from apps.fila.views import CheckinView, PrevisaoView

app_name = "fila"

urlpatterns = [
    path("checkins/", CheckinView.as_view(), name="checkin"),
    path("fila/previsao/", PrevisaoView.as_view(), name="previsao"),
]
