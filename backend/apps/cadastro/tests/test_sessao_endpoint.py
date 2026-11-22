"""POST, GET e DELETE /api/sessao/ (RF03.1 a RF03.3, ADR 0007, Cadastro N4 4c).

O cliente exige CSRF, como o navegador: pega o cookie em GET /api/csrf/ e
manda o `X-CSRFToken` (#112). O login troca o token, então quem escreve
depois dele lê o cookie de novo (`atualizar_csrf`).
"""

import logging
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cadastro.models import StatusUsuario
from config.parametros import AvisoPrivacidadeConfig

ROTA = "/api/sessao/"
SENHA = "senha-forte-123"
MATRICULA = "202400001"
EMAIL = "202400001@aluno.unb.br"
AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def novo_cliente():
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get("/api/csrf/")
    atualizar_csrf(cliente)
    return cliente


def atualizar_csrf(cliente):
    """Manda no cabeçalho o valor atual do cookie, como o apiClient do PWA."""
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)


@pytest.fixture
def cliente(db):
    return novo_cliente()


def criar_conta(status=StatusUsuario.ATIVO, versao="teste"):
    return get_user_model().objects.create_user(
        matricula_siape=MATRICULA,
        tipo_usuario="estudante",
        apelido="cris",
        email_institucional=EMAIL,
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita=versao,
        password=SENHA,
        status=status,
        email_confirmado=status != StatusUsuario.PENDENTE,
    )


@pytest.fixture
def conta(db):
    return criar_conta()


def entrar(cliente, email=EMAIL, senha=SENHA):
    return cliente.post(
        ROTA, {"emailInstitucional": email, "senha": senha}, format="json"
    )


@pytest.fixture
def logado(cliente, conta):
    assert entrar(cliente).status_code == 200
    atualizar_csrf(cliente)
    return cliente


def assert_erro(resposta, status, codigo):
    assert resposta.status_code == status
    corpo = resposta.json()
    assert set(corpo) == {"codigo", "mensagem"}
    assert corpo["codigo"] == codigo
    assert corpo["mensagem"]
    return corpo


# --- POST: login (RF03.1) -----------------------------------------------------


def test_login_devolve_200_com_apelido_tipo_e_aviso(cliente, conta):
    resposta = entrar(cliente)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "apelido": "cris",
        "tipo": "estudante",
        "avisoPrivacidadePendente": True,
    }


def test_login_grava_o_cookie_de_sessao(cliente, conta):
    resposta = entrar(cliente)

    cookie = resposta.cookies["sessionid"]
    assert cookie.value
    assert cookie["httponly"]


def test_login_abre_a_sessao_da_conta(cliente, conta):
    entrar(cliente)

    assert cliente.get(ROTA).status_code == 200
    sessao = Session.objects.get().get_decoded()
    assert sessao["_auth_user_id"] == str(conta.pk)


def test_login_troca_o_csrftoken(cliente, conta):
    """ADR 0007: o Django gira o token no login; o PWA relê o cookie."""
    antes = cliente.cookies["csrftoken"].value

    resposta = entrar(cliente)

    assert resposta.cookies["csrftoken"].value != antes


def test_login_troca_o_id_da_sessao_anterior(cliente, conta):
    """Fixação de sessão: o id de antes do login não vale depois dele."""
    cliente.cookies["sessionid"] = "id-escolhido-por-um-atacante"

    resposta = entrar(cliente)

    assert resposta.cookies["sessionid"].value != "id-escolhido-por-um-atacante"


def test_login_de_professor_com_nome_arroba_unb(cliente, db):
    """ADR 0002: professor/servidor entra com qualquer texto antes de @unb.br."""
    get_user_model().objects.create_user(
        matricula_siape="1234567",
        tipo_usuario="professor_servidor",
        apelido="dani",
        email_institucional="maria.silva@unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita=AvisoPrivacidadeConfig.versao_atual,
        password=SENHA,
        status=StatusUsuario.ATIVO,
        email_confirmado=True,
    )

    resposta = entrar(cliente, email="Maria.Silva@unb.br")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "apelido": "dani",
        "tipo": "professor_servidor",
        "avisoPrivacidadePendente": False,
    }


@pytest.mark.parametrize(
    "email",
    [f" {EMAIL} ", "  202400001@ALUNO.unb.BR ", "202400001@Aluno.UnB.br"],
)
def test_maiusculas_e_espacos_em_volta_do_email_entram_na_mesma_conta(
    cliente, conta, email
):
    resposta = entrar(cliente, email=email)

    assert resposta.status_code == 200
    sessao = Session.objects.get().get_decoded()
    assert sessao["_auth_user_id"] == str(conta.pk)


# --- POST: mensagem genérica (RF03.1) -----------------------------------------


def test_senha_errada_da_401_credenciais_invalidas(cliente, conta):
    resposta = entrar(cliente, senha="senha-errada")

    corpo = assert_erro(resposta, 401, "credenciais_invalidas")
    assert corpo["mensagem"] == "E-mail ou senha incorretos."


def test_conta_inexistente_e_senha_errada_dao_a_mesma_resposta(cliente, conta):
    """Não revela se o e-mail tem conta (RF03.1)."""
    senha_errada = entrar(cliente, senha="senha-errada")
    inexistente = entrar(cliente, email="202400002@aluno.unb.br")

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json()
    assert inexistente.json() == {
        "codigo": "credenciais_invalidas",
        "mensagem": "E-mail ou senha incorretos.",
    }
    assert "matrícula" not in inexistente.json()["mensagem"].lower()


def test_professor_inexistente_e_senha_errada_dao_a_mesma_resposta(cliente, conta):
    """O domínio @unb.br também não revela se a conta existe (RF03.1)."""
    senha_errada = entrar(cliente, senha="senha-errada")
    inexistente = entrar(cliente, email="ninguem.aqui@unb.br")

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json()


@pytest.mark.parametrize("status", [StatusUsuario.SUSPENSO])
def test_conta_suspensa_ou_removida_da_a_mesma_mensagem_generica(cliente, status, db):
    criar_conta(status=status)

    resposta = entrar(cliente)
    corpo = assert_erro(resposta, 401, "credenciais_invalidas")

    assert corpo == entrar(cliente, email="202400002@aluno.unb.br").json()


def test_login_recusado_nao_abre_sessao(cliente, conta):
    entrar(cliente, senha="senha-errada")

    assert cliente.get(ROTA).status_code == 401
    assert not Session.objects.exists()


# --- POST: conta pendente -----------------------------------------------------


def test_conta_pendente_recebe_403_com_convite_a_confirmar(cliente, db):
    criar_conta(status=StatusUsuario.PENDENTE)

    resposta = entrar(cliente)

    corpo = assert_erro(resposta, 403, "conta_nao_confirmada")
    assert "confirm" in corpo["mensagem"].lower()
    assert cliente.get(ROTA).status_code == 401


def test_conta_pendente_com_senha_errada_recebe_a_mensagem_generica(cliente, db):
    criar_conta(status=StatusUsuario.PENDENTE)

    assert_erro(entrar(cliente, senha="senha-errada"), 401, "credenciais_invalidas")


# --- POST: bloqueio (RF03.2) --------------------------------------------------


@pytest.fixture
def relogio():
    with mock.patch("django.utils.timezone.now", return_value=AGORA) as agora:
        yield agora


def test_quinto_erro_responde_429_login_bloqueado(cliente, conta, relogio):
    for _ in range(4):
        assert_erro(entrar(cliente, senha="senha-errada"), 401, "credenciais_invalidas")

    resposta = entrar(cliente, senha="senha-errada")

    corpo = assert_erro(resposta, 429, "login_bloqueado")
    assert "10 min" in corpo["mensagem"]
    assert resposta["Retry-After"] == str(10 * 60)


def test_sexta_tentativa_bloqueada_mesmo_com_a_senha_certa(cliente, conta, relogio):
    for _ in range(5):
        entrar(cliente, senha="senha-errada")
    relogio.return_value = AGORA + timedelta(minutes=7, seconds=30)

    resposta = entrar(cliente)

    corpo = assert_erro(resposta, 429, "login_bloqueado")
    # Arredonda para cima: com 2 min 30 s restando, diz 3 min.
    assert "3 min" in corpo["mensagem"]
    assert resposta["Retry-After"] == str(150)
    assert cliente.get(ROTA).status_code == 401


def test_depois_de_10_minutos_o_login_volta_a_funcionar(cliente, conta, relogio):
    for _ in range(5):
        entrar(cliente, senha="senha-errada")
    relogio.return_value = AGORA + timedelta(minutes=10)

    assert entrar(cliente).status_code == 200


# --- POST: corpo inválido -----------------------------------------------------


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"emailInstitucional": EMAIL},
        {"senha": SENHA},
        {"emailInstitucional": "", "senha": SENHA},
        {"emailInstitucional": EMAIL, "senha": ""},
        {"emailInstitucional": None, "senha": SENHA},
        # Número no JSON não vira texto.
        {"emailInstitucional": 202400001, "senha": SENHA},
        {"emailInstitucional": EMAIL, "senha": 12345678},
        {"emailInstitucional": "a" * 250 + "@unb.br", "senha": SENHA},
    ],
)
def test_corpo_invalido_da_422_dados_invalidos(cliente, conta, corpo):
    resposta = cliente.post(ROTA, corpo, format="json")

    corpo_erro = assert_erro(resposta, 422, "dados_invalidos")
    assert corpo_erro["mensagem"] == "Informe o seu e-mail institucional e a senha."
    conta.refresh_from_db()
    assert conta.tentativas_login_falhas == 0


def test_corpo_com_matricula_siape_da_422(cliente, conta):
    """O campo antigo não vale mais: o login é pelo e-mail institucional."""
    resposta = cliente.post(
        ROTA, {"matriculaSiape": MATRICULA, "senha": SENHA}, format="json"
    )

    corpo = assert_erro(resposta, 422, "dados_invalidos")
    assert corpo["mensagem"] == "Informe o seu e-mail institucional e a senha."
    assert cliente.get(ROTA).status_code == 401
    conta.refresh_from_db()
    assert conta.tentativas_login_falhas == 0


@pytest.mark.parametrize(
    "email",
    [
        MATRICULA,
        "x@gmail.com",
        "202400001@aluno.unb.br.com",
        "a@b@unb.br",
        "nome @unb.br",
        "202.400.001",
    ],
)
def test_email_fora_do_dominio_da_422_e_nao_conta_tentativa(cliente, conta, email):
    """ADR 0002: @aluno.unb.br ou @unb.br. Formato é público: não conta erro."""
    corpo = assert_erro(entrar(cliente, email=email), 422, "dados_invalidos")

    assert "e-mail institucional" in corpo["mensagem"]
    assert "matrícula" not in corpo["mensagem"].lower()
    conta.refresh_from_db()
    assert conta.tentativas_login_falhas == 0


# --- ADR 0008 e RI10: nada de matrícula/SIAPE, e-mail ou senha ----------------


def test_respostas_da_sessao_nao_trazem_matricula_nem_email(cliente, conta):
    respostas = [entrar(cliente), cliente.get(ROTA)]

    for resposta in respostas:
        assert resposta.status_code == 200
        assert set(resposta.json()) == {"apelido", "tipo", "avisoPrivacidadePendente"}
        conteudo = resposta.content.decode()
        assert MATRICULA not in conteudo
        assert EMAIL not in conteudo


def test_login_nao_registra_email_matricula_nem_senha_no_log(cliente, conta, caplog):
    with caplog.at_level(logging.DEBUG):
        entrar(cliente, senha="senha-errada-123")
        entrar(cliente, email="202400002@aluno.unb.br", senha="senha-errada-123")
        entrar(cliente, email="x@gmail.com", senha="senha-errada-123")
        entrar(cliente, email="maria.silva@unb.br", senha="senha-errada-123")
        for _ in range(5):
            entrar(cliente, email=" 202400001@ALUNO.unb.br ", senha="senha-errada-123")
        entrar(cliente)

    for registro in caplog.records:
        mensagem = registro.getMessage().lower()
        assert MATRICULA not in mensagem
        # Sem "@" nenhum: pega o e-mail de estudante, de professor e o de fora.
        assert "@" not in mensagem
        assert "senha-errada-123" not in mensagem
        assert SENHA not in mensagem


def test_bloqueio_vai_para_o_log_so_com_o_id_da_conta(cliente, conta, caplog):
    with caplog.at_level(logging.WARNING, logger="apps.cadastro"):
        for _ in range(5):
            entrar(cliente, senha="senha-errada")

    mensagens = [r.getMessage() for r in caplog.records]
    assert any("bloqueado" in m and str(conta.pk) in m for m in mensagens)


# --- GET: quem sou eu ---------------------------------------------------------


def test_get_sem_sessao_da_401(cliente):
    assert_erro(cliente.get(ROTA), 401, "nao_autenticado")


def test_get_com_aviso_antigo_diz_que_o_aviso_esta_pendente(logado):
    assert logado.get(ROTA).json()["avisoPrivacidadePendente"] is True


def test_get_com_aviso_atual_diz_que_nao_ha_pendencia(cliente, db):
    criar_conta(versao=AvisoPrivacidadeConfig.versao_atual)
    entrar(cliente)

    assert cliente.get(ROTA).json() == {
        "apelido": "cris",
        "tipo": "estudante",
        "avisoPrivacidadePendente": False,
    }


@pytest.mark.parametrize("status", [StatusUsuario.SUSPENSO])
def test_conta_suspensa_perde_a_sessao_aberta(logado, conta, status):
    """ADR 0007: a sessão já aberta deixa de autenticar na requisição seguinte."""
    get_user_model().objects.filter(pk=conta.pk).update(status=status)

    assert_erro(logado.get(ROTA), 401, "nao_autenticado")


# --- DELETE: logout (RF03.3) --------------------------------------------------


def test_logout_devolve_204_e_encerra_a_sessao(logado):
    resposta = logado.delete(ROTA)

    assert resposta.status_code == 204
    assert not resposta.content
    assert_erro(logado.get(ROTA), 401, "nao_autenticado")
    assert not Session.objects.exists()


def test_logout_encerra_so_a_sessao_atual(logado, conta):
    """Outro aparelho logado na mesma conta continua logado."""
    outro_aparelho = novo_cliente()
    entrar(outro_aparelho)

    logado.delete(ROTA)

    assert outro_aparelho.get(ROTA).status_code == 200


def test_logout_sem_sessao_da_401(cliente):
    assert_erro(cliente.delete(ROTA), 401, "nao_autenticado")


def test_logout_sem_csrf_da_403_e_nao_desloga(logado):
    logado.credentials()

    assert_erro(logado.delete(ROTA), 403, "csrf_invalido")
    assert logado.get(ROTA).status_code == 200
