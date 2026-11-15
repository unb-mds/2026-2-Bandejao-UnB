"""POST /api/cadastro/: cenários Gherkin do RF01 (RF01.1 a RF01.5).

O cliente exige CSRF, como o navegador: pega o cookie em GET /api/csrf/ e
manda o `X-CSRFToken` (#112, #120).
"""

from datetime import date
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.cadastro.erros import MENSAGEM_JA_CADASTRADO

Usuario = get_user_model()
ROTA = "/api/cadastro/"


@pytest.fixture(autouse=True)
def hoje_fixo():
    """2º semestre de 2026: o último prefixo de matrícula aceito é 262."""
    with mock.patch(
        "apps.cadastro.validadores.timezone.localdate", return_value=date(2026, 11, 14)
    ):
        yield


@pytest.fixture
def cliente(db):
    cliente = APIClient(enforce_csrf_checks=True)
    resposta = cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=resposta.cookies["csrftoken"].value)
    return cliente


def estudante(**extra):
    return {
        "tipoUsuario": "estudante",
        "emailInstitucional": "251098732@aluno.unb.br",
        "apelido": "cris",
        "senha": "senha-forte-123",
        "aceitePrivacidade": True,
        **extra,
    }


def professor(**extra):
    return {
        "tipoUsuario": "professor_servidor",
        "emailInstitucional": "maria.silva@unb.br",
        "matriculaSiape": "1234567",
        "senha": "senha-forte-123",
        "aceitePrivacidade": True,
        **extra,
    }


def assert_422(resposta, trecho=None):
    assert resposta.status_code == 422
    corpo = resposta.json()
    # Formato do projeto, nunca o {"campo": [...]} do DRF (#112, item 4).
    assert set(corpo) == {"codigo", "mensagem"}
    assert corpo["codigo"] == "dados_invalidos"
    if trecho:
        assert trecho in corpo["mensagem"]
    return corpo


# --- RF01.1: duas etapas, senha e aviso de privacidade -----------------------


def test_cadastro_de_estudante_cria_conta_pendente(cliente):
    resposta = cliente.post(ROTA, estudante(), format="json")

    assert resposta.status_code == 201
    assert resposta.json() == {
        "emailInstitucional": "251098732@aluno.unb.br",
        "status": "pendente",
    }
    assert Usuario.objects.get().status == "pendente"


def test_rejeitado_nao_grava_nada(cliente):
    cliente.post(ROTA, estudante(senha="curta"), format="json")

    assert not Usuario.objects.exists()


def test_senha_com_menos_de_8_caracteres_e_rejeitada(cliente):
    resposta = cliente.post(ROTA, estudante(senha="1234567"), format="json")

    assert_422(resposta, "no mínimo 8 caracteres")


def test_sem_ciencia_do_aviso_de_privacidade_e_rejeitado(cliente):
    resposta = cliente.post(ROTA, estudante(aceitePrivacidade=False), format="json")

    assert_422(resposta, "aviso de privacidade")


def test_sem_o_campo_do_aviso_e_rejeitado(cliente):
    dados = estudante()
    del dados["aceitePrivacidade"]

    resposta = cliente.post(ROTA, dados, format="json")

    assert_422(resposta, "aviso de privacidade")


def test_tipo_de_usuario_desconhecido_e_rejeitado(cliente):
    resposta = cliente.post(ROTA, estudante(tipoUsuario="visitante"), format="json")

    assert_422(resposta, "aluno, professor ou servidor")


def test_corpo_vazio_da_422_no_formato_do_projeto(cliente):
    assert_422(cliente.post(ROTA, {}, format="json"))


# --- RF01.2 e RF01.3: Estudante e matrícula (RN01) ---------------------------


def test_matricula_extraida_do_email(cliente):
    cliente.post(ROTA, estudante(), format="json")

    assert Usuario.objects.get().matricula_siape == "251098732"


@pytest.mark.parametrize(
    "email",
    ["251098732@unb.br", "251098732@gmail.com", "251098732@aluno.unb.br.com"],
)
def test_email_de_estudante_fora_do_formato(cliente, email):
    resposta = cliente.post(ROTA, estudante(emailInstitucional=email), format="json")

    assert_422(resposta, "matricula@aluno.unb.br")


@pytest.mark.parametrize(
    ("matricula", "trecho"),
    [
        ("25109873", "9 dígitos"),  # 8 dígitos (L10)
        ("25109873a", "9 dígitos"),  # letra
        ("091098732", "semestre de ingresso"),  # antes de 2010
        ("253098732", "semestre de ingresso"),  # 3º dígito inválido
        ("271098732", "semestre de ingresso"),  # semestre futuro
        ("251123456", "Confira os dígitos"),  # crescente
        ("251654321", "Confira os dígitos"),  # decrescente
        ("251111111", "Confira os dígitos"),  # todos iguais
    ],
)
def test_matricula_impossivel_e_rejeitada_com_mensagem_especifica(
    cliente, matricula, trecho
):
    resposta = cliente.post(
        ROTA, estudante(emailInstitucional=f"{matricula}@aluno.unb.br"), format="json"
    )

    assert_422(resposta, trecho)


def test_novo_semestre_aceito_sem_mudar_codigo(cliente):
    with mock.patch(
        "apps.cadastro.validadores.timezone.localdate", return_value=date(2027, 2, 1)
    ):
        resposta = cliente.post(
            ROTA, estudante(emailInstitucional="271098732@aluno.unb.br"), format="json"
        )

    assert resposta.status_code == 201


@pytest.mark.parametrize("apelido", ["ab", "a" * 21, "com espaco"])
def test_apelido_de_estudante_fora_da_rn02(cliente, apelido):
    resposta = cliente.post(ROTA, estudante(apelido=apelido), format="json")

    assert_422(resposta, "3 a 20 caracteres")


def test_estudante_sem_apelido_e_rejeitado(cliente):
    dados = estudante()
    del dados["apelido"]

    assert_422(cliente.post(ROTA, dados, format="json"), "3 a 20 caracteres")


# --- RF01.4: Professor/Servidor ----------------------------------------------


def test_professor_ganha_apelido_do_email(cliente):
    resposta = cliente.post(ROTA, professor(), format="json")

    assert resposta.status_code == 201
    conta = Usuario.objects.get()
    assert conta.apelido == "mariasilva"
    assert conta.matricula_siape == "1234567"
    assert conta.tipo_usuario == "professor_servidor"


@pytest.mark.parametrize("siape", ["123456", "12345678", "123456a"])
def test_siape_fora_de_7_digitos(cliente, siape):
    resposta = cliente.post(ROTA, professor(matriculaSiape=siape), format="json")

    assert_422(resposta, "7 dígitos")


def test_professor_sem_siape(cliente):
    dados = professor()
    del dados["matriculaSiape"]

    assert_422(cliente.post(ROTA, dados, format="json"), "7 dígitos")


@pytest.mark.parametrize("email", ["maria@gmail.com", "maria@aluno.unb.br"])
def test_email_de_professor_fora_do_dominio_unb(cliente, email):
    resposta = cliente.post(ROTA, professor(emailInstitucional=email), format="json")

    assert_422(resposta, "@unb.br")


# --- RF01.5: unicidade --------------------------------------------------------


def test_email_repetido_e_rejeitado(cliente):
    cliente.post(ROTA, professor(), format="json")

    resposta = cliente.post(ROTA, professor(matriculaSiape="7654321"), format="json")

    corpo = assert_422(resposta)
    assert corpo["mensagem"] == MENSAGEM_JA_CADASTRADO
    assert Usuario.objects.count() == 1


def test_matricula_repetida_e_rejeitada(cliente):
    cliente.post(ROTA, professor(), format="json")

    resposta = cliente.post(
        ROTA, professor(emailInstitucional="outra@unb.br"), format="json"
    )

    corpo = assert_422(resposta)
    assert corpo["mensagem"] == MENSAGEM_JA_CADASTRADO
    assert Usuario.objects.count() == 1


def test_mensagem_nao_revela_qual_campo_ja_existe(cliente):
    """Matrícula repetida e e-mail repetido dão exatamente a mesma resposta."""
    cliente.post(ROTA, professor(), format="json")

    so_email = cliente.post(ROTA, professor(matriculaSiape="7654321"), format="json")
    so_siape = cliente.post(
        ROTA, professor(emailInstitucional="outra@unb.br"), format="json"
    )
    os_dois = cliente.post(ROTA, professor(), format="json")

    assert so_email.status_code == so_siape.status_code == os_dois.status_code
    assert so_email.json() == so_siape.json() == os_dois.json()
    mensagem = so_email.json()["mensagem"].lower()
    assert "matrícula/siape ou e-mail" in mensagem


def test_conta_pendente_tambem_bloqueia_o_email(cliente):
    cliente.post(ROTA, estudante(), format="json")
    assert Usuario.objects.get().status == "pendente"

    resposta = cliente.post(ROTA, estudante(apelido="outro"), format="json")

    assert_422(resposta)


def test_apelido_digitado_repetido_sem_distinguir_maiusculas(cliente):
    cliente.post(ROTA, estudante(), format="json")

    resposta = cliente.post(
        ROTA,
        estudante(emailInstitucional="251098733@aluno.unb.br", apelido="CRIS"),
        format="json",
    )

    corpo = assert_422(resposta)
    assert corpo["mensagem"] == "Este apelido já está em uso. Escolha outro."


def test_apelido_extraido_em_uso_da_409_com_sugestao(cliente):
    cliente.post(
        ROTA,
        estudante(apelido="mariasilva"),
        format="json",
    )

    resposta = cliente.post(ROTA, professor(), format="json")

    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["codigo"] == "apelido_indisponivel"
    assert corpo["apelidoSugerido"] == "mariasilva1"
    assert corpo["mensagem"]
    assert Usuario.objects.count() == 1


def test_apelido_extraido_fora_do_tamanho_da_409(cliente):
    resposta = cliente.post(
        ROTA, professor(emailInstitucional="a.b@unb.br"), format="json"
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "apelido_indisponivel"


def test_depois_do_409_o_professor_reenvia_com_apelido_digitado(cliente):
    cliente.post(ROTA, estudante(apelido="mariasilva"), format="json")
    sugestao = cliente.post(ROTA, professor(), format="json").json()["apelidoSugerido"]

    resposta = cliente.post(ROTA, professor(apelido=sugestao), format="json")

    assert resposta.status_code == 201
    assert Usuario.objects.get(tipo_usuario="professor_servidor").apelido == sugestao


# --- CSRF (#112) --------------------------------------------------------------


def test_cadastro_sem_token_csrf_e_recusado(db):
    resposta = APIClient(enforce_csrf_checks=True).post(
        ROTA, estudante(), format="json"
    )

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "csrf_invalido"
    assert not Usuario.objects.exists()
