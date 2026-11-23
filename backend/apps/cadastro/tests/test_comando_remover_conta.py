"""`manage.py remover_conta` (BD-12, #164): o jeito de a equipe excluir a conta."""

from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.gamificacao.models import PontuacaoUsuario
from apps.gamificacao.pontuacao_service import PontuacaoService

Usuario = get_user_model()

pytestmark = pytest.mark.django_db


def criar_conta(numero):
    conta = Usuario.objects.create_user(
        matricula_siape=f"2025{numero:05d}",
        tipo_usuario="estudante",
        apelido=f"pessoa{numero}",
        email_institucional=f"2025{numero:05d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    PontuacaoService().inicializar_conta(conta)
    return conta


def rodar(*argumentos):
    saida = StringIO()
    call_command("remover_conta", *argumentos, stdout=saida)
    return saida.getvalue()


def test_exclui_a_conta_pelo_id_e_os_contadores_vao_junto():
    conta = criar_conta(1)
    rodar(str(conta.pk))
    assert not Usuario.objects.filter(pk=conta.pk).exists()
    assert not PontuacaoUsuario.objects.filter(usuario_id=conta.pk).exists()


def test_outras_contas_ficam_intactas():
    conta = criar_conta(1)
    outra = criar_conta(2)
    rodar(str(conta.pk))
    assert Usuario.objects.filter(pk=outra.pk).exists()
    assert PontuacaoUsuario.objects.filter(usuario=outra).exists()


def test_conta_que_nao_existe_avisa_e_sai_com_erro():
    outra = criar_conta(2)
    with pytest.raises(CommandError, match="não existe"):
        rodar("999999")
    assert Usuario.objects.filter(pk=outra.pk).exists()


def test_id_que_nao_e_numero_e_recusado():
    with pytest.raises(CommandError):
        rodar("abc")


def test_sem_o_id_e_recusado():
    with pytest.raises(CommandError):
        rodar()


def test_saida_leva_so_o_id_sem_dado_pessoal():
    conta = criar_conta(1)
    saida = rodar(str(conta.pk))
    assert saida.strip() == f"Conta {conta.pk} excluída."
    for dado in (conta.matricula_siape, conta.email_institucional, conta.apelido):
        assert dado not in saida


def test_conta_apagada_no_meio_do_caminho_avisa():
    """Outro processo apagou a conta entre a busca e a exclusão."""
    conta = criar_conta(1)
    alvo = "apps.cadastro.management.commands.remover_conta.RemoverContaCommand"
    with (
        mock.patch(f"{alvo}.executar", return_value=False),
        pytest.raises(CommandError, match="já foi excluída"),
    ):
        rodar(str(conta.pk))
