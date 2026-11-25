"""ConfirmacaoEmailService (RF02.1, RF02.2, Cadastro N4 4b).

Os cenários do HTTP (status e corpo) ficam em `test_confirmacao_email_endpoint.py`.
Aqui ficam o token (hash, prazo, uso único), o e-mail e o reenvio.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from smtplib import SMTPException, SMTPRecipientsRefused, SMTPResponseException
from unittest import mock

import pytest
from django.core import mail

from apps.cadastro.confirmacao_email_service import (
    ConfirmacaoEmailService,
)
from apps.cadastro.erros import TokenExpiradoOuInvalidoError
from apps.cadastro.models import StatusUsuario, TipoToken, Token
from config.parametros import ParametrosCadastroConfig

AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def servico():
    return ConfirmacaoEmailService()


@pytest.fixture
def relogio():
    """Troca o `timezone.now` do Django (também usado pelo `auto_now_add`)."""
    with mock.patch("django.utils.timezone.now", return_value=AGORA) as agora:
        yield agora


def hash_de(token):
    return hashlib.sha256(token.encode()).hexdigest()


def token_do_email(mensagem):
    """Tira o token do link `.../confirmar-email?token=<token>` do e-mail."""
    return mensagem.body.split("confirmar-email?token=")[1].split()[0]


def enviar_e_pegar_token(servico, conta):
    mail.outbox.clear()
    servico.enviar_link(conta)
    assert len(mail.outbox) == 1
    return token_do_email(mail.outbox[0])


# --- enviar_link --------------------------------------------------------------


def test_enviar_link_manda_um_email_para_o_email_institucional(
    servico, usuario, relogio
):
    servico.enviar_link(usuario)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["202400001@aluno.unb.br"]


def test_o_link_aponta_para_o_pwa_e_nao_para_a_api(servico, usuario, settings):
    settings.URL_DO_PWA = "https://bandejao.exemplo.br/"

    servico.enviar_link(usuario)

    corpo = mail.outbox[0].body
    assert "https://bandejao.exemplo.br/confirmar-email?token=" in corpo
    assert "/api/" not in corpo


def test_o_remetente_e_o_padrao_do_projeto(servico, usuario, settings):
    settings.DEFAULT_FROM_EMAIL = "nao-responda@bandejaounb.com.br"

    servico.enviar_link(usuario)

    assert mail.outbox[0].from_email == "nao-responda@bandejaounb.com.br"


def test_so_o_hash_do_token_e_guardado(servico, usuario):
    token = enviar_e_pegar_token(servico, usuario)

    salvo = Token.objects.get(usuario=usuario)
    assert salvo.tipo == TipoToken.CONFIRMACAO_EMAIL
    assert salvo.token_hash == hash_de(token)
    assert not Token.objects.filter(token_hash=token).exists()


def test_o_token_e_aleatorio_e_longo(servico, usuario):
    primeiro = enviar_e_pegar_token(servico, usuario)
    segundo = enviar_e_pegar_token(servico, usuario)

    assert primeiro != segundo
    # secrets.token_urlsafe(32): 43 caracteres.
    assert len(primeiro) >= 43


def test_o_link_vale_24_horas(servico, usuario, relogio):
    servico.enviar_link(usuario)

    salvo = Token.objects.get(usuario=usuario)
    assert ParametrosCadastroConfig.validade_confirmacao_email == timedelta(hours=24)
    assert salvo.criado_em == AGORA
    assert salvo.expira_em == AGORA + timedelta(hours=24)


def test_enviar_link_invalida_os_tokens_anteriores_da_conta(servico, usuario):
    antigo = enviar_e_pegar_token(servico, usuario)
    novo = enviar_e_pegar_token(servico, usuario)

    assert Token.objects.get(token_hash=hash_de(antigo)).usado_em is not None
    assert Token.objects.get(token_hash=hash_de(novo)).usado_em is None
    with pytest.raises(TokenExpiradoOuInvalidoError):
        servico.confirmar(antigo)


def test_enviar_link_diz_se_o_email_saiu(servico, usuario):
    """O reenvio só gasta a vaga do limite por conta quando o e-mail sai (#123)."""
    assert servico.enviar_link(usuario) is True

    with mock.patch(
        "apps.cadastro.confirmacao_email_service.send_mail",
        side_effect=SMTPException("fora do ar"),
    ):
        assert servico.enviar_link(usuario) is False


def test_falha_no_smtp_mantem_o_link_anterior_valido(servico, usuario):
    """Se o e-mail novo não sai, o link que a pessoa já tem continua valendo."""
    antigo = enviar_e_pegar_token(servico, usuario)

    with mock.patch(
        "apps.cadastro.confirmacao_email_service.send_mail",
        side_effect=SMTPException("fora do ar"),
    ):
        servico.enviar_link(usuario)

    servico.confirmar(antigo)
    usuario.refresh_from_db()
    assert usuario.status == StatusUsuario.ATIVO


def test_falha_no_smtp_nao_deixa_token_novo_no_banco(servico, usuario):
    """O token que não foi entregue não pode renovar o prazo do job (RF02.3)."""
    enviar_e_pegar_token(servico, usuario)

    with mock.patch(
        "apps.cadastro.confirmacao_email_service.send_mail",
        side_effect=SMTPException("fora do ar"),
    ):
        servico.enviar_link(usuario)

    assert Token.objects.filter(usuario=usuario).count() == 1


def test_erro_que_nao_e_do_envio_nao_e_engolido(servico, usuario):
    """Um erro de programação tem que aparecer (500 com traceback), não sumir."""
    with (
        mock.patch(
            "apps.cadastro.confirmacao_email_service.send_mail",
            side_effect=RuntimeError("bug"),
        ),
        pytest.raises(RuntimeError),
    ):
        servico.enviar_link(usuario)


def test_falha_de_rede_tambem_e_tratada(servico, usuario, caplog):
    """Servidor SMTP fora do ar dá OSError (ConnectionRefusedError, timeout)."""
    with (
        mock.patch(
            "apps.cadastro.confirmacao_email_service.send_mail",
            side_effect=ConnectionRefusedError("recusado"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        servico.enviar_link(usuario)

    assert "ConnectionRefusedError" in caplog.text


def test_o_log_da_falha_traz_o_codigo_smtp(servico, usuario, caplog):
    with (
        mock.patch(
            "apps.cadastro.confirmacao_email_service.send_mail",
            side_effect=SMTPResponseException(421, b"servico indisponivel"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        servico.enviar_link(usuario)

    assert "421" in caplog.text


def test_o_log_da_recusa_do_destinatario_nao_traz_o_endereco(servico, usuario, caplog):
    """`SMTPRecipientsRefused` guarda o endereço recusado dentro da exceção."""
    recusa = SMTPRecipientsRefused({"202400001@aluno.unb.br": (550, b"nao existe")})
    with (
        mock.patch(
            "apps.cadastro.confirmacao_email_service.send_mail", side_effect=recusa
        ),
        caplog.at_level(logging.ERROR),
    ):
        servico.enviar_link(usuario)

    assert "SMTPRecipientsRefused" in caplog.text
    assert "202400001" not in caplog.text


def test_o_email_diz_a_validade_do_link(servico, usuario):
    servico.enviar_link(usuario)

    assert "24 horas" in mail.outbox[0].body


def test_falha_no_smtp_nao_levanta_e_vai_para_o_log_sem_token_nem_email(
    servico, usuario, caplog
):
    with (
        mock.patch(
            "apps.cadastro.confirmacao_email_service.send_mail",
            side_effect=SMTPException("recusado: 202400001@aluno.unb.br"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        servico.enviar_link(usuario)

    mensagens = " ".join(r.getMessage() for r in caplog.records)
    assert "SMTPException" in mensagens
    assert "202400001" not in mensagens
    assert "confirmar-email?token=" not in mensagens
    assert all(r.exc_info is None for r in caplog.records)


# --- confirmar ----------------------------------------------------------------


def test_token_valido_confirma_a_conta(servico, usuario):
    token = enviar_e_pegar_token(servico, usuario)

    servico.confirmar(token)

    usuario.refresh_from_db()
    assert usuario.email_confirmado is True
    assert usuario.status == StatusUsuario.ATIVO
    assert Token.objects.get(usuario=usuario).usado_em is not None


def test_token_um_segundo_antes_de_expirar_ainda_confirma(servico, usuario, relogio):
    token = enviar_e_pegar_token(servico, usuario)
    relogio.return_value = (
        AGORA
        + ParametrosCadastroConfig.validade_confirmacao_email
        - timedelta(seconds=1)
    )

    servico.confirmar(token)

    usuario.refresh_from_db()
    assert usuario.status == StatusUsuario.ATIVO


def test_token_expirado_levanta_erro(servico, usuario, relogio):
    token = enviar_e_pegar_token(servico, usuario)
    relogio.return_value = AGORA + ParametrosCadastroConfig.validade_confirmacao_email

    with pytest.raises(TokenExpiradoOuInvalidoError):
        servico.confirmar(token)

    usuario.refresh_from_db()
    assert usuario.status == StatusUsuario.PENDENTE
    assert usuario.email_confirmado is False


def test_token_ja_usado_levanta_erro(servico, usuario):
    token = enviar_e_pegar_token(servico, usuario)
    servico.confirmar(token)

    with pytest.raises(TokenExpiradoOuInvalidoError):
        servico.confirmar(token)


def test_token_inexistente_levanta_erro(servico, db):
    with pytest.raises(TokenExpiradoOuInvalidoError):
        servico.confirmar("nao-existe")


def test_token_de_outro_tipo_nao_confirma(servico, usuario, relogio):
    Token.objects.create(
        usuario=usuario,
        tipo=TipoToken.REDEFINICAO_SENHA,
        token_hash=hash_de("token-de-senha"),
        expira_em=AGORA + timedelta(hours=1),
    )

    with pytest.raises(TokenExpiradoOuInvalidoError):
        servico.confirmar("token-de-senha")


def test_conta_que_nao_esta_pendente_nao_e_reativada_pelo_link(servico, usuario):
    token = enviar_e_pegar_token(servico, usuario)
    usuario.status = StatusUsuario.SUSPENSO
    usuario.save()

    with pytest.raises(TokenExpiradoOuInvalidoError):
        servico.confirmar(token)

    usuario.refresh_from_db()
    assert usuario.status == StatusUsuario.SUSPENSO


def test_confirmar_trava_o_token_com_select_for_update(servico, usuario):
    """Dois cliques no mesmo link: o segundo espera o primeiro e vê `usado_em`.

    Este teste confere a trava, e não a corrida: o SQLite dos testes ignora o
    `FOR UPDATE` (ele trava o banco inteiro na escrita). A corrida de verdade só
    acontece no MySQL de produção. O comportamento de uso único (o segundo
    clique dá erro) está em `test_token_ja_usado_levanta_erro`.
    """
    token = enviar_e_pegar_token(servico, usuario)

    with mock.patch.object(
        Token.objects, "select_for_update", wraps=Token.objects.select_for_update
    ) as travar:
        servico.confirmar(token)

    travar.assert_called_once()


# --- conta_para_reenvio e reenviar -------------------------------------------


def test_acha_a_conta_pelo_email(servico, usuario):
    assert servico.conta_para_reenvio(email="202400001@aluno.unb.br") == usuario


def test_acha_a_conta_pelo_email_com_maiusculas_e_espacos_nas_pontas(servico, usuario):
    assert servico.conta_para_reenvio(email=" 202400001@ALUNO.unb.br ") == usuario


def test_reenvio_pela_matricula_pura_nao_acha_conta(servico, usuario):
    """O reenvio não confere domínio: só não acha conta (e a resposta é 200)."""
    assert servico.conta_para_reenvio(email="202400001") is None


def test_acha_a_conta_pelo_token_mesmo_expirado_ou_usado(servico, usuario, relogio):
    token = enviar_e_pegar_token(servico, usuario)
    servico.enviar_link(usuario)  # o primeiro fica marcado como usado
    relogio.return_value = AGORA + timedelta(days=2)

    assert servico.conta_para_reenvio(token=token) == usuario


def test_conta_inexistente_da_none(servico, db):
    assert servico.conta_para_reenvio(email="209999999@aluno.unb.br") is None
    assert servico.conta_para_reenvio(token="nao-existe") is None


def test_reenviar_renova_o_prazo(servico, usuario, relogio):
    servico.enviar_link(usuario)
    depois = AGORA + timedelta(hours=20)
    relogio.return_value = depois
    mail.outbox.clear()

    servico.reenviar(usuario)

    assert len(mail.outbox) == 1
    novo = Token.objects.filter(usuario=usuario, usado_em__isnull=True).get()
    assert novo.expira_em == depois + timedelta(hours=24)


def test_reenviar_para_conta_confirmada_nao_manda_email(servico, usuario):
    token = enviar_e_pegar_token(servico, usuario)
    servico.confirmar(token)
    usuario.refresh_from_db()
    mail.outbox.clear()

    servico.reenviar(usuario)

    assert mail.outbox == []


def test_reenviar_sem_conta_nao_faz_nada(servico, db):
    servico.reenviar(None)

    assert mail.outbox == []


def test_email_e_token_juntos_vale_o_email(servico, usuario):
    outra = type(usuario).objects.create_user(
        matricula_siape="202400002",
        tipo_usuario="estudante",
        apelido="outra",
        email_institucional="202400002@aluno.unb.br",
        aceite_privacidade_em=usuario.aceite_privacidade_em,
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    token_da_outra = enviar_e_pegar_token(servico, outra)

    conta = servico.conta_para_reenvio(
        email="202400001@aluno.unb.br", token=token_da_outra
    )

    assert conta == usuario


def test_email_sem_conta_e_token_valido_vale_o_token(servico, usuario):
    """Se o e-mail não acha conta, o token que veio junto ainda é tentado."""
    token = enviar_e_pegar_token(servico, usuario)

    conta = servico.conta_para_reenvio(email="209999999@aluno.unb.br", token=token)

    assert conta == usuario


def test_email_e_token_sem_conta_nao_acham_conta(servico, usuario):
    assert (
        servico.conta_para_reenvio(email="209999999@aluno.unb.br", token="nao-existe")
        is None
    )


def test_token_de_outro_tipo_nao_acha_conta_para_reenvio(servico, usuario, relogio):
    Token.objects.create(
        usuario=usuario,
        tipo=TipoToken.REDEFINICAO_SENHA,
        token_hash=hash_de("token-de-senha"),
        expira_em=AGORA + timedelta(hours=1),
    )

    assert servico.conta_para_reenvio(token="token-de-senha") is None


def test_reenviar_para_conta_suspensa_nao_manda_email(servico, usuario):
    usuario.status = StatusUsuario.SUSPENSO
    usuario.save()

    servico.reenviar(usuario)

    assert mail.outbox == []
