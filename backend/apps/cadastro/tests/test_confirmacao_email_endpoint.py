"""POST /api/confirmar-email/{token}/ e POST /api/reenviar-confirmacao/ (RF02).

O cliente exige CSRF, como o navegador: pega o cookie em GET /api/csrf/ e
manda o `X-CSRFToken` (#112, #120). O envio do link no cadastro também fica
aqui, porque é o fluxo que o PWA vê: cadastrar, receber o e-mail, confirmar.
"""

from datetime import date, timedelta
from smtplib import SMTPException
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import OperationalError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cadastro.confirmacao_email_service import ConfirmacaoEmailService
from apps.cadastro.models import StatusUsuario

Usuario = get_user_model()
ROTA_REENVIO = "/api/reenviar-confirmacao/"


def rota_confirmacao(token):
    return f"/api/confirmar-email/{token}/"


@pytest.fixture
def cliente(db):
    cliente = APIClient(enforce_csrf_checks=True)
    resposta = cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=resposta.cookies["csrftoken"].value)
    return cliente


def token_do_email(mensagem):
    return mensagem.body.split("confirmar-email?token=")[1].split()[0]


@pytest.fixture
def token(usuario):
    """Token em claro do link enviado à conta pendente `usuario`."""
    ConfirmacaoEmailService().enviar_link(usuario)
    token = token_do_email(mail.outbox[-1])
    mail.outbox.clear()
    return token


def assert_410(resposta):
    assert resposta.status_code == 410
    corpo = resposta.json()
    assert set(corpo) == {"codigo", "mensagem"}
    assert corpo["codigo"] == "token_invalido_ou_expirado"
    assert corpo["mensagem"]


# --- POST /api/confirmar-email/{token}/ (RF02.1) ------------------------------


def test_confirmacao_valida_da_200_e_ativa_a_conta(cliente, usuario, token):
    resposta = cliente.post(rota_confirmacao(token), format="json")

    assert resposta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.email_confirmado is True
    assert usuario.status == StatusUsuario.ATIVO


def test_link_invalido_da_410(cliente):
    assert_410(cliente.post(rota_confirmacao("nao-existe"), format="json"))


def test_link_ja_usado_da_410(cliente, token):
    cliente.post(rota_confirmacao(token), format="json")

    assert_410(cliente.post(rota_confirmacao(token), format="json"))


def test_link_expirado_da_410(cliente, usuario, token):
    daqui_a_dois_dias = timezone.now() + timedelta(days=2)
    with mock.patch("django.utils.timezone.now", return_value=daqui_a_dois_dias):
        resposta = cliente.post(rota_confirmacao(token), format="json")

    assert_410(resposta)
    usuario.refresh_from_db()
    assert usuario.status == StatusUsuario.PENDENTE


def test_confirmacao_sem_csrf_da_403(usuario, token):
    resposta = APIClient(enforce_csrf_checks=True).post(rota_confirmacao(token))

    assert resposta.status_code == 403
    usuario.refresh_from_db()
    assert usuario.status == StatusUsuario.PENDENTE


# --- POST /api/reenviar-confirmacao/ (RF02.2) ---------------------------------


def test_reenvio_pelo_email_manda_um_email(cliente, usuario):
    resposta = cliente.post(
        ROTA_REENVIO, {"emailInstitucional": "202400001@aluno.unb.br"}, format="json"
    )

    assert resposta.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [usuario.email_institucional]


def test_reenvio_pelo_email_em_maiusculas_acha_a_conta(cliente, usuario):
    resposta = cliente.post(
        ROTA_REENVIO,
        {"emailInstitucional": "  202400001@ALUNO.UnB.br "},
        format="json",
    )

    assert resposta.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [usuario.email_institucional]


def test_reenvio_pela_matricula_siape_antiga_da_422(cliente, usuario):
    """O campo antigo não vale mais: o reenvio pela tela de login é por e-mail."""
    resposta = cliente.post(
        ROTA_REENVIO, {"matriculaSiape": "202400001"}, format="json"
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert corpo["mensagem"] == (
        "Informe o seu e-mail institucional ou abra o link recebido."
    )
    assert mail.outbox == []


def test_reenvio_pelo_token_expirado_manda_um_email(cliente, usuario, token):
    daqui_a_dois_dias = timezone.now() + timedelta(days=2)
    with mock.patch("django.utils.timezone.now", return_value=daqui_a_dois_dias):
        resposta = cliente.post(ROTA_REENVIO, {"token": token}, format="json")

    assert resposta.status_code == 200
    assert len(mail.outbox) == 1


def test_o_link_reenviado_confirma_a_conta(cliente, usuario, token):
    cliente.post(ROTA_REENVIO, {"token": token}, format="json")
    novo = token_do_email(mail.outbox[0])

    assert_410(cliente.post(rota_confirmacao(token), format="json"))
    assert cliente.post(rota_confirmacao(novo), format="json").status_code == 200


def test_reenvio_para_conta_inexistente_da_o_mesmo_200_sem_email(cliente, usuario):
    existente = cliente.post(
        ROTA_REENVIO, {"emailInstitucional": "202400001@aluno.unb.br"}, format="json"
    )
    mail.outbox.clear()

    inexistente = cliente.post(
        ROTA_REENVIO, {"emailInstitucional": "209999999@aluno.unb.br"}, format="json"
    )
    # Fora do domínio: o reenvio não dá 422, só não acha conta (RF02.2).
    fora_do_dominio = cliente.post(
        ROTA_REENVIO, {"emailInstitucional": "x@gmail.com"}, format="json"
    )
    token_falso = cliente.post(ROTA_REENVIO, {"token": "nao-existe"}, format="json")

    for resposta in (inexistente, fora_do_dominio, token_falso):
        assert resposta.status_code == existente.status_code == 200
        assert resposta.content == existente.content
    assert mail.outbox == []


def test_reenvio_para_conta_confirmada_da_o_mesmo_200_sem_email(
    cliente, usuario, token
):
    cliente.post(rota_confirmacao(token), format="json")

    resposta = cliente.post(
        ROTA_REENVIO, {"emailInstitucional": "202400001@aluno.unb.br"}, format="json"
    )

    assert resposta.status_code == 200
    assert mail.outbox == []


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"emailInstitucional": ""},
        {"token": ""},
        {"emailInstitucional": 202400001},
        {"emailInstitucional": None},
    ],
)
def test_reenvio_sem_email_e_sem_token_da_422(cliente, corpo):
    resposta = cliente.post(ROTA_REENVIO, corpo, format="json")

    assert resposta.status_code == 422
    corpo_resposta = resposta.json()
    assert set(corpo_resposta) == {"codigo", "mensagem"}
    assert corpo_resposta["codigo"] == "dados_invalidos"
    assert mail.outbox == []


# --- Envio do link no cadastro (CadastroService -> ConfirmacaoEmailService) ---


@pytest.fixture
def hoje_fixo():
    with mock.patch(
        "apps.cadastro.validadores.timezone.localdate", return_value=date(2026, 11, 14)
    ):
        yield


CADASTRO = {
    "tipoUsuario": "estudante",
    "emailInstitucional": "251098732@aluno.unb.br",
    "apelido": "cris",
    "senha": "senha-forte-123",
    "aceitePrivacidade": True,
}


def test_cadastro_manda_um_email_com_o_link_do_pwa(
    cliente, hoje_fixo, settings, django_capture_on_commit_callbacks
):
    settings.URL_DO_PWA = "https://bandejao.exemplo.br"

    with django_capture_on_commit_callbacks(execute=True):
        resposta = cliente.post("/api/cadastro/", CADASTRO, format="json")

    assert resposta.status_code == 201
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["251098732@aluno.unb.br"]
    assert "https://bandejao.exemplo.br/confirmar-email?token=" in mail.outbox[0].body


def test_cadastro_recusado_nao_manda_email(
    cliente, hoje_fixo, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        resposta = cliente.post(
            "/api/cadastro/", {**CADASTRO, "senha": "curta"}, format="json"
        )

    assert resposta.status_code == 422
    assert mail.outbox == []


def test_falha_no_smtp_nao_desfaz_o_cadastro(
    cliente, hoje_fixo, django_capture_on_commit_callbacks
):
    with (
        mock.patch(
            "apps.cadastro.confirmacao_email_service.send_mail",
            side_effect=SMTPException("fora do ar"),
        ),
        django_capture_on_commit_callbacks(execute=True),
    ):
        resposta = cliente.post("/api/cadastro/", CADASTRO, format="json")

    assert resposta.status_code == 201
    conta = Usuario.objects.get(matricula_siape="251098732")
    assert conta.status == StatusUsuario.PENDENTE


def test_o_link_do_cadastro_confirma_a_conta(
    cliente, hoje_fixo, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        cliente.post("/api/cadastro/", CADASTRO, format="json")
    token = token_do_email(mail.outbox[0])

    resposta = cliente.post(rota_confirmacao(token), format="json")

    assert resposta.status_code == 200
    conta = Usuario.objects.get(matricula_siape="251098732")
    assert conta.status == StatusUsuario.ATIVO


@pytest.mark.django_db(transaction=True)
def test_falha_de_banco_ao_criar_o_link_nao_derruba_o_cadastro(hoje_fixo, caplog):
    """Com commit de verdade, o on_commit roda dentro da requisição.

    Os testes com `django_capture_on_commit_callbacks` rodam o callback depois
    da resposta, então não pegam uma exceção que sobe depois do COMMIT. Aqui a
    conta já está gravada: devolver 500 faria a pessoa tentar de novo e
    receber "já cadastrado".
    """
    cliente = APIClient(enforce_csrf_checks=True)
    resposta_csrf = cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=resposta_csrf.cookies["csrftoken"].value)

    with mock.patch(
        "apps.cadastro.confirmacao_email_service.Token.objects.create",
        side_effect=OperationalError("database is locked"),
    ):
        resposta = cliente.post("/api/cadastro/", CADASTRO, format="json")

    assert resposta.status_code == 201
    conta = Usuario.objects.get(matricula_siape="251098732")
    assert conta.status == StatusUsuario.PENDENTE
    assert "OperationalError" in caplog.text
    assert mail.outbox == []
