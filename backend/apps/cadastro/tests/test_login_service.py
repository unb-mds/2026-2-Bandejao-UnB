"""LoginService (RF03.1, RF03.2, ADR 0002, Cadastro N4 4c).

Os cenários do HTTP (status, corpo e cookie) ficam em `test_sessao_endpoint.py`.
"""

from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone

from apps.cadastro.erros import (
    ContaNaoConfirmadaError,
    CredenciaisInvalidasError,
    IdentificadorInvalidoError,
    LoginBloqueadoError,
)
from apps.cadastro.login_service import LoginService
from apps.cadastro.models import StatusUsuario

AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
SENHA = "senha-forte-123"
EMAIL = "202400001@aluno.unb.br"
EMAIL_PROFESSOR = "dani.souza@unb.br"


@pytest.fixture
def servico():
    return LoginService()


@pytest.fixture
def relogio():
    with mock.patch("django.utils.timezone.now", return_value=AGORA) as agora:
        yield agora


def criar_conta(identificador="202400001", status=StatusUsuario.ATIVO, **extra):
    estudante = len(identificador) == 9
    return get_user_model().objects.create_user(
        matricula_siape=identificador,
        tipo_usuario="estudante" if estudante else "professor_servidor",
        apelido=extra.pop("apelido", "cris"),
        email_institucional=(
            f"{identificador}@aluno.unb.br" if estudante else EMAIL_PROFESSOR
        ),
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password=SENHA,
        status=status,
        email_confirmado=status != StatusUsuario.PENDENTE,
        **extra,
    )


@pytest.fixture
def conta(db):
    return criar_conta()


def errar(servico, email, vezes):
    for _ in range(vezes):
        with pytest.raises((CredenciaisInvalidasError, LoginBloqueadoError)):
            servico.autenticar(email, "senha-errada")


# --- RF03.1 e ADR 0002: e-mail institucional --------------------------------


def test_estudante_entra_com_matricula_arroba_aluno(servico, conta):
    assert servico.autenticar(EMAIL, SENHA) == conta


def test_professor_entra_com_nome_arroba_unb(servico, db):
    professor = criar_conta("1234567", apelido="dani")

    assert servico.autenticar(EMAIL_PROFESSOR, SENHA) == professor


@pytest.mark.parametrize(
    "email",
    [
        "  202400001@ALUNO.unb.br ",
        "202400001@Aluno.UnB.Br",
        "\t202400001@aluno.unb.br\n",
    ],
)
def test_maiusculas_e_espacos_nas_pontas_entram_na_mesma_conta(servico, conta, email):
    assert servico.autenticar(email, SENHA) == conta


def test_professor_com_maiusculas_entra_na_mesma_conta(servico, db):
    professor = criar_conta("1234567", apelido="dani")

    assert servico.autenticar(" Dani.Souza@UNB.br ", SENHA) == professor


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        "202400001",
        "1234567",
        "x@gmail.com",
        "202400001@aluno.unb.br.com",
        "a@b@unb.br",
        "nome@unb.br.evil.com",
        "nome @unb.br",
        "@unb.br",
        "nome@outro.unb.br",
    ],
)
def test_email_fora_do_formato_e_recusado_antes_da_busca(servico, email, db):
    """ADR 0002: @aluno.unb.br ou @unb.br. O resto nem consulta o banco."""
    with (
        mock.patch(
            "apps.cadastro.login_service.ContaRepository.buscar_por_email"
        ) as buscar,
        pytest.raises(IdentificadorInvalidoError) as erro,
    ):
        servico.autenticar(email, SENHA)

    buscar.assert_not_called()
    assert "e-mail institucional" in erro.value.mensagem
    assert "matrícula" not in erro.value.mensagem.lower()


def test_email_fora_do_formato_nao_conta_tentativa(servico, conta):
    for email in ("202400001", "202400001@gmail.com"):
        with pytest.raises(IdentificadorInvalidoError):
            servico.autenticar(email, "senha-errada")

    conta.refresh_from_db()
    assert conta.tentativas_login_falhas == 0


def test_senha_errada_e_recusada(servico, conta):
    with pytest.raises(CredenciaisInvalidasError):
        servico.autenticar(EMAIL, "senha-errada")


def test_conta_inexistente_da_o_mesmo_erro_da_senha_errada(servico, db):
    """Mensagem genérica: não revela se o e-mail tem conta (RF03.1)."""
    with pytest.raises(CredenciaisInvalidasError):
        servico.autenticar("202400002@aluno.unb.br", SENHA)


def test_conta_inexistente_tambem_calcula_um_hash(servico, db):
    """Sem isso, a resposta mais rápida revelaria que a conta não existe."""
    with (
        mock.patch(
            "apps.cadastro.login_service.make_password", return_value="x"
        ) as hash_falso,
        pytest.raises(CredenciaisInvalidasError),
    ):
        servico.autenticar("202400002@aluno.unb.br", SENHA)

    hash_falso.assert_called_once_with(SENHA)


def test_espacos_da_senha_fazem_parte_dela(servico, db):
    conta = criar_conta()
    conta.set_password(" senha-forte-123 ")
    conta.save()

    with pytest.raises(CredenciaisInvalidasError):
        servico.autenticar(EMAIL, SENHA)
    assert servico.autenticar(EMAIL, " senha-forte-123 ") == conta


# --- Conta pendente e conta suspensa -----------------------------------


def test_conta_pendente_com_senha_certa_pede_confirmacao(servico, db):
    criar_conta(status=StatusUsuario.PENDENTE)

    with pytest.raises(ContaNaoConfirmadaError):
        servico.autenticar(EMAIL, SENHA)


def test_conta_pendente_com_senha_errada_nao_revela_a_pendencia(servico, db):
    """Só quem sabe a senha descobre que a conta existe e está pendente."""
    criar_conta(status=StatusUsuario.PENDENTE)

    with pytest.raises(CredenciaisInvalidasError):
        servico.autenticar(EMAIL, "senha-errada")


def test_conta_suspensa_recebe_a_mensagem_generica(servico, db):
    """ADR 0004 e 0007: `is_active = False` não entra, com a mesma mensagem."""
    criar_conta(status=StatusUsuario.SUSPENSO)

    with pytest.raises(CredenciaisInvalidasError):
        servico.autenticar(EMAIL, SENHA)


# --- RF03.2: bloqueio após tentativas malsucedidas ----------------------------


def test_quatro_erros_ainda_deixam_entrar(servico, conta, relogio):
    errar(servico, EMAIL, 4)

    assert servico.autenticar(EMAIL, SENHA) == conta


def test_quinto_erro_ja_avisa_do_bloqueio(servico, conta, relogio):
    """Como o simulado do front (#119): o 5º erro já responde que bloqueou."""
    errar(servico, EMAIL, 4)

    with pytest.raises(LoginBloqueadoError) as erro:
        servico.autenticar(EMAIL, "senha-errada")

    assert erro.value.segundos_restantes == 10 * 60


def test_bloqueado_nem_com_a_senha_certa(servico, conta, relogio):
    """A 6ª tentativa fica bloqueada, mesmo que a senha esteja certa (RF03.2)."""
    errar(servico, EMAIL, 5)
    relogio.return_value = AGORA + timedelta(minutes=4)

    with pytest.raises(LoginBloqueadoError) as erro:
        servico.autenticar(EMAIL, SENHA)

    assert erro.value.segundos_restantes == 6 * 60


def test_tentativa_durante_o_bloqueio_nao_estende_o_bloqueio(servico, conta, relogio):
    errar(servico, EMAIL, 5)
    relogio.return_value = AGORA + timedelta(minutes=9)
    errar(servico, EMAIL, 3)

    relogio.return_value = AGORA + timedelta(minutes=10)

    assert servico.autenticar(EMAIL, SENHA) == conta


def test_bloqueio_acaba_em_10_minutos(servico, conta, relogio):
    errar(servico, EMAIL, 5)
    relogio.return_value = AGORA + timedelta(minutes=10)

    assert servico.autenticar(EMAIL, SENHA) == conta


def test_acerto_zera_os_erros(servico, conta, relogio):
    errar(servico, EMAIL, 4)
    servico.autenticar(EMAIL, SENHA)

    errar(servico, EMAIL, 4)

    assert servico.autenticar(EMAIL, SENHA) == conta


def test_conta_pendente_com_senha_certa_tambem_zera_os_erros(servico, db, relogio):
    """Senha certa não é tentativa malsucedida, mesmo sem poder entrar ainda."""
    pendente = criar_conta(status=StatusUsuario.PENDENTE)
    errar(servico, EMAIL, 4)

    with pytest.raises(ContaNaoConfirmadaError):
        servico.autenticar(EMAIL, SENHA)

    pendente.refresh_from_db()
    assert pendente.tentativas_login_falhas == 0


def test_conta_suspensa_tambem_e_bloqueada(servico, db, relogio):
    """Senão, a falta do 429 diria que a senha testada era a certa."""
    criar_conta(status=StatusUsuario.SUSPENSO)
    errar(servico, EMAIL, 4)

    with pytest.raises(LoginBloqueadoError):
        servico.autenticar(EMAIL, SENHA)


def test_bloqueio_e_por_conta(servico, conta, db, relogio):
    outra = criar_conta("1234567", apelido="dani")
    errar(servico, EMAIL, 5)

    assert servico.autenticar(EMAIL_PROFESSOR, SENHA) == outra


def test_erros_com_o_email_em_caixas_diferentes_contam_na_mesma_conta(
    servico, conta, relogio
):
    """Trocar maiúsculas ou pôr espaços não escapa do bloqueio (RF03.2)."""
    for variacao in [
        "202400001@aluno.unb.br",
        "202400001@ALUNO.UNB.BR",
        " 202400001@aluno.unb.br",
        "202400001@Aluno.unb.br ",
    ]:
        with pytest.raises(CredenciaisInvalidasError):
            servico.autenticar(variacao, "senha-errada")

    with pytest.raises(LoginBloqueadoError):
        servico.autenticar("  202400001@aluno.UNB.br  ", "senha-errada")

    conta.refresh_from_db()
    assert conta.tentativas_login_falhas == 5


def test_bloqueio_vem_antes_da_conferencia_da_senha(servico, conta, relogio):
    """Bloqueado, a senha nem é conferida: não dá para seguir adivinhando."""
    errar(servico, EMAIL, 5)

    with (
        mock.patch.object(type(conta), "check_password") as conferir,
        pytest.raises(LoginBloqueadoError),
    ):
        servico.autenticar(EMAIL, SENHA)

    conferir.assert_not_called()


# --- Trava da conta (RF03.2) --------------------------------------------------


def test_login_trava_a_conta_com_select_for_update(servico, conta):
    """Sem a trava, tentativas simultâneas perdem contagem e passam do limite.

    O SQLite dos testes ignora o `FOR UPDATE`: aqui se confere o pedido da
    trava na linha da conta, e não a corrida, que só acontece no MySQL.
    """
    with (
        mock.patch.object(
            QuerySet,
            "select_for_update",
            autospec=True,
            side_effect=QuerySet.select_for_update,
        ) as travar,
        pytest.raises(CredenciaisInvalidasError),
    ):
        servico.autenticar(EMAIL, "senha-errada")

    contas_travadas = [
        chamada.args[0]
        for chamada in travar.call_args_list
        if chamada.args[0].model is get_user_model()
    ]
    assert len(contas_travadas) == 1


def test_login_pede_a_busca_com_trava(servico, conta):
    with mock.patch(
        "apps.cadastro.login_service.ContaRepository.buscar_por_email",
        autospec=True,
        return_value=conta,
    ) as buscar:
        servico.autenticar(EMAIL, SENHA)

    buscar.assert_called_once_with(mock.ANY, EMAIL, travar=True)
