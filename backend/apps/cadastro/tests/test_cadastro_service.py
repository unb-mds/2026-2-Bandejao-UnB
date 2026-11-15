"""CadastroService.registrar (RF01, RN01, RN02, Cadastro N4 4a).

Os cenários do HTTP (status e corpo) ficam em `test_cadastro_endpoint.py`.
Aqui ficam a ordem das checagens, o que é gravado e a transação.
"""

from datetime import date
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.cadastro.apelido_resolver import ApelidoIndisponivelError
from apps.cadastro.cadastro_service import CadastroService
from apps.cadastro.erros import (
    MENSAGEM_JA_CADASTRADO,
    CadastroInvalidoError,
    EmailJaCadastradoError,
    IdentificadorJaCadastradoError,
)
from apps.cadastro.models import StatusUsuario, TipoUsuario
from apps.gamificacao.models import PontuacaoUsuario
from config.parametros import AvisoPrivacidadeConfig

Usuario = get_user_model()
HOJE = date(2026, 11, 14)


@pytest.fixture
def servico():
    return CadastroService(hoje=HOJE)


def dados_estudante(**extra):
    return {
        "emailInstitucional": "251098732@aluno.unb.br",
        "apelido": "cris",
        "senha": "senha-forte-123",
        "aceitePrivacidade": True,
        **extra,
    }


def dados_professor(**extra):
    return {
        "emailInstitucional": "maria.silva@unb.br",
        "matriculaSiape": "1234567",
        "senha": "senha-forte-123",
        "aceitePrivacidade": True,
        **extra,
    }


# --- O que é gravado ---------------------------------------------------------


@pytest.mark.django_db
def test_estudante_gravado_pendente_com_matricula_do_email(servico):
    conta = servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    conta.refresh_from_db()
    assert conta.tipo_usuario == TipoUsuario.ESTUDANTE
    assert conta.matricula_siape == "251098732"
    assert conta.email_institucional == "251098732@aluno.unb.br"
    assert conta.apelido == "cris"
    assert conta.status == StatusUsuario.PENDENTE
    assert conta.email_confirmado is False


@pytest.mark.django_db
def test_professor_gravado_com_apelido_extraido_do_email(servico):
    conta = servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    assert conta.matricula_siape == "1234567"
    assert conta.apelido == "mariasilva"


@pytest.mark.django_db
def test_professor_depois_do_409_usa_o_apelido_digitado(servico):
    conta = servico.registrar(
        TipoUsuario.PROFESSOR_SERVIDOR, dados_professor(apelido="Profa_Maria")
    )

    assert conta.apelido == "Profa_Maria"


@pytest.mark.django_db
def test_senha_gravada_como_hash(servico):
    conta = servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    assert conta.password != "senha-forte-123"
    assert conta.check_password("senha-forte-123")


@pytest.mark.django_db
def test_email_gravado_em_minusculas(servico):
    conta = servico.registrar(
        TipoUsuario.ESTUDANTE,
        dados_estudante(emailInstitucional="251098732@ALUNO.UNB.BR"),
    )

    assert conta.email_institucional == "251098732@aluno.unb.br"


@pytest.mark.django_db
def test_aceite_grava_a_versao_atual_do_aviso_e_a_hora(servico):
    """RNF07.1: a conta nasce sem pendência de aviso de privacidade."""
    conta = servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    assert conta.versao_aviso_aceita == AvisoPrivacidadeConfig.versao_atual
    assert conta.aceite_privacidade_em is not None


@pytest.mark.django_db
def test_conta_nasce_com_pontuacao_zerada(servico):
    conta = servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    pontuacao = PontuacaoUsuario.objects.get(usuario=conta)
    assert pontuacao.pontos_totais == 0
    assert pontuacao.sequencia_atual == 0


# --- Transação ---------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_nada_e_gravado_se_a_pontuacao_falhar(servico):
    """Cadastro N4 4a: conta e contadores na mesma transação."""
    with (
        mock.patch(
            "apps.gamificacao.pontuacao_service.PontuacaoService.inicializar_conta",
            side_effect=RuntimeError("falhou"),
        ),
        pytest.raises(RuntimeError),
    ):
        servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    assert not Usuario.objects.exists()
    assert not PontuacaoUsuario.objects.exists()


@pytest.mark.django_db
def test_corrida_na_unicidade_vira_erro_de_cadastro(servico):
    """Dois cadastros iguais ao mesmo tempo: o UNIQUE do banco decide."""
    with (
        mock.patch(
            "apps.cadastro.models.UsuarioManager.create_user",
            side_effect=IntegrityError("UNIQUE"),
        ),
        pytest.raises(CadastroInvalidoError) as erro,
    ):
        servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    assert erro.value.mensagem == MENSAGEM_JA_CADASTRADO


# --- Ordem das checagens -----------------------------------------------------


@pytest.mark.django_db
def test_sem_aceite_e_rejeitado_antes_de_tudo(servico):
    with pytest.raises(CadastroInvalidoError) as erro:
        servico.registrar(
            TipoUsuario.ESTUDANTE,
            dados_estudante(aceitePrivacidade=False, emailInstitucional="x"),
        )

    assert "aviso de privacidade" in erro.value.mensagem


@pytest.mark.django_db
def test_duplicidade_e_conferida_antes_do_apelido(servico):
    """Sem isso, o 409 do apelido diria que o e-mail ainda está livre."""
    servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    with pytest.raises(EmailJaCadastradoError):
        servico.registrar(
            TipoUsuario.PROFESSOR_SERVIDOR, dados_professor(matriculaSiape="7654321")
        )


@pytest.mark.django_db
def test_matricula_repetida(servico):
    servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    with pytest.raises(IdentificadorJaCadastradoError):
        servico.registrar(
            TipoUsuario.PROFESSOR_SERVIDOR,
            dados_professor(emailInstitucional="outra@unb.br"),
        )


@pytest.mark.django_db
def test_duplicados_tem_a_mesma_mensagem(servico):
    """RF01.5 com a decisão do contrato: não diz qual dos dois já existe."""
    assert IdentificadorJaCadastradoError().mensagem == MENSAGEM_JA_CADASTRADO
    assert EmailJaCadastradoError().mensagem == MENSAGEM_JA_CADASTRADO


@pytest.mark.django_db
def test_apelido_extraido_em_uso_levanta_o_erro_recuperavel(servico):
    servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante(apelido="mariasilva"))

    with pytest.raises(ApelidoIndisponivelError):
        servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    assert Usuario.objects.count() == 1
