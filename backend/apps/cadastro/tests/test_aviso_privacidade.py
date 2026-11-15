"""Ciência do aviso de privacidade (RF11, RNF07.1, Cadastro N4 4d).

`Usuario.aviso_privacidade_pendente()`, `AvisoPrivacidadeService` e
`POST /api/privacidade/aceite/`.
"""

from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.cadastro.aviso_privacidade_service import AvisoPrivacidadeService
from config.parametros import AvisoPrivacidadeConfig

ROTA = "/api/privacidade/aceite/"
AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def logado(usuario):
    """Cliente que exige CSRF, logado na conta `usuario` (aviso antigo)."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.force_login(usuario)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    return cliente


# --- Usuario.aviso_privacidade_pendente() -------------------------------------


def test_versao_antiga_deixa_o_aviso_pendente(usuario):
    usuario.versao_aviso_aceita = "2026-01-01"

    assert usuario.aviso_privacidade_pendente() is True


def test_versao_atual_nao_deixa_pendencia(usuario):
    usuario.versao_aviso_aceita = AvisoPrivacidadeConfig.versao_atual

    assert usuario.aviso_privacidade_pendente() is False


def test_versao_nova_do_aviso_volta_a_gerar_pendencia(usuario):
    """Trocar a versão no config basta: nenhum código muda (Cadastro N4 4d)."""
    usuario.versao_aviso_aceita = AvisoPrivacidadeConfig.versao_atual

    with mock.patch.object(AvisoPrivacidadeConfig, "versao_atual", "2027-01-01"):
        assert usuario.aviso_privacidade_pendente() is True


# --- AvisoPrivacidadeService.registrar_ciencia --------------------------------


def test_registrar_ciencia_grava_a_versao_atual_e_a_hora(usuario):
    AvisoPrivacidadeService().registrar_ciencia(usuario, AGORA)

    usuario.refresh_from_db()
    assert usuario.versao_aviso_aceita == AvisoPrivacidadeConfig.versao_atual
    assert usuario.aceite_privacidade_em == AGORA
    assert usuario.aviso_privacidade_pendente() is False


def test_registrar_de_novo_mantem_a_hora_do_primeiro_aceite(usuario):
    """O primeiro aceite da versão é a prova do consentimento (RNF07.1)."""
    servico = AvisoPrivacidadeService()
    servico.registrar_ciencia(usuario, AGORA)

    servico.registrar_ciencia(usuario, AGORA + timedelta(days=1))

    usuario.refresh_from_db()
    assert usuario.aceite_privacidade_em == AGORA


def test_registrar_ciencia_grava_so_os_campos_do_aviso(usuario):
    """Não sobrescreve o resto da conta com uma cópia velha da memória."""
    type(usuario).objects.filter(pk=usuario.pk).update(status="suspenso")

    AvisoPrivacidadeService().registrar_ciencia(usuario, AGORA)

    usuario.refresh_from_db()
    assert usuario.status == "suspenso"


# --- POST /api/privacidade/aceite/ --------------------------------------------


def test_aceite_devolve_204_sem_corpo(logado):
    resposta = logado.post(ROTA)

    assert resposta.status_code == 204
    assert not resposta.content


def test_aceite_usa_a_hora_do_servidor(logado, usuario):
    with mock.patch("django.utils.timezone.now", return_value=AGORA):
        logado.post(ROTA)

    usuario.refresh_from_db()
    assert usuario.aceite_privacidade_em == AGORA
    assert usuario.versao_aviso_aceita == AvisoPrivacidadeConfig.versao_atual


def test_aceite_ignora_versao_e_hora_vindas_do_corpo(logado, usuario):
    logado.post(
        ROTA,
        {"versao": "2020-01-01", "aceitoEm": "2020-01-01T00:00:00Z"},
        format="json",
    )

    usuario.refresh_from_db()
    assert usuario.versao_aviso_aceita == AvisoPrivacidadeConfig.versao_atual
    assert usuario.aceite_privacidade_em.year != 2020


def test_depois_do_aceite_a_sessao_diz_que_nao_ha_pendencia(logado):
    assert logado.get("/api/sessao/").json()["avisoPrivacidadePendente"] is True

    logado.post(ROTA)

    assert logado.get("/api/sessao/").json()["avisoPrivacidadePendente"] is False


def test_aceite_sem_sessao_da_401(db):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)

    resposta = cliente.post(ROTA)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"
