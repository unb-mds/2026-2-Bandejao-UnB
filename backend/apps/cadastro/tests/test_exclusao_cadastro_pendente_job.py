"""ExclusaoCadastroPendenteJob (RF02.3, Cadastro N4 4b).

O prazo conta do último link enviado (o reenvio renova), e não da criação da
conta. A exclusão é pelo ORM, para os tokens e a pontuação irem junto.
"""

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.cadastro.confirmacao_email_service import ConfirmacaoEmailService
from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.management.commands.excluir_cadastros_pendentes import (
    ExclusaoCadastroPendenteJob,
)
from apps.cadastro.models import StatusUsuario, Token
from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.pontuacao_service import PontuacaoService

Usuario = get_user_model()
INICIO = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def relogio():
    with mock.patch("django.utils.timezone.now", return_value=INICIO) as agora:
        yield agora


def criar_conta(numero):
    conta = Usuario.objects.create_user(
        matricula_siape=f"2024{numero:05d}",
        tipo_usuario="estudante",
        apelido=f"conta{numero}",
        email_institucional=f"2024{numero:05d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    PontuacaoService().inicializar_conta(conta)
    return conta


@pytest.fixture
def pendente(db, relogio):
    conta = criar_conta(1)
    ConfirmacaoEmailService().enviar_link(conta)
    return conta


def existe(conta):
    return Usuario.objects.filter(pk=conta.pk).exists()


def test_apaga_a_pendente_com_o_ultimo_link_ha_mais_de_24_horas(pendente, relogio):
    relogio.return_value = INICIO + timedelta(hours=24, seconds=1)

    excluidas = ExclusaoCadastroPendenteJob().executar()

    assert excluidas == 1
    assert not existe(pendente)
    # CASCADE: nada da conta fica para trás.
    assert not Token.objects.filter(usuario_id=pendente.pk).exists()
    assert not PontuacaoUsuario.objects.filter(usuario_id=pendente.pk).exists()


def test_nao_apaga_a_pendente_dentro_das_24_horas(pendente, relogio):
    relogio.return_value = INICIO + timedelta(hours=23)

    assert ExclusaoCadastroPendenteJob().executar() == 0
    assert existe(pendente)


def test_nao_apaga_a_pendente_que_pediu_reenvio_dentro_das_24_horas(pendente, relogio):
    relogio.return_value = INICIO + timedelta(hours=20)
    ConfirmacaoEmailService().reenviar(pendente)
    # 30 h depois do cadastro, mas só 10 h depois do reenvio.
    relogio.return_value = INICIO + timedelta(hours=30)

    assert ExclusaoCadastroPendenteJob().executar() == 0
    assert existe(pendente)


def test_nao_apaga_conta_confirmada(db, relogio):
    conta = criar_conta(2)
    servico = ConfirmacaoEmailService()
    servico.enviar_link(conta)
    token = mail.outbox[-1].body.split("confirmar-email?token=")[1].split()[0]
    servico.confirmar(token)
    relogio.return_value = INICIO + timedelta(days=3)

    assert ExclusaoCadastroPendenteJob().executar() == 0
    conta.refresh_from_db()
    assert conta.status == StatusUsuario.ATIVO


def test_nao_apaga_conta_suspensa(pendente, relogio):
    pendente.status = StatusUsuario.SUSPENSO
    pendente.save()
    relogio.return_value = INICIO + timedelta(days=3)

    assert ExclusaoCadastroPendenteJob().executar() == 0
    assert existe(pendente)


def test_pendente_sem_nenhum_link_conta_da_criacao_da_conta(db, relogio):
    """Se o envio nem chegou a criar o token, o prazo vem do `criado_em` da conta."""
    sem_link = criar_conta(3)
    relogio.return_value = INICIO + timedelta(hours=25)

    assert ExclusaoCadastroPendenteJob().executar() == 1
    assert not existe(sem_link)


def test_so_apaga_as_expiradas(pendente, relogio):
    relogio.return_value = INICIO + timedelta(hours=10)
    recente = criar_conta(4)
    ConfirmacaoEmailService().enviar_link(recente)
    relogio.return_value = INICIO + timedelta(hours=25)

    assert ExclusaoCadastroPendenteJob().executar() == 1
    assert not existe(pendente)
    assert existe(recente)


def test_o_comando_do_django_roda_o_job(pendente, relogio):
    relogio.return_value = INICIO + timedelta(days=2)
    saida = StringIO()

    call_command("excluir_cadastros_pendentes", stdout=saida)

    assert not existe(pendente)
    assert "1" in saida.getvalue()


def test_a_exclusao_confere_o_prazo_de_novo(pendente):
    """Entre a listagem do job e a exclusão, a pessoa pode ter pedido reenvio."""
    limite_antes_do_link = INICIO - timedelta(hours=1)

    apagou = ContaRepository().excluir_pendente_expirada(pendente, limite_antes_do_link)

    assert apagou is False
    assert existe(pendente)
