"""CadastroService.registrar (RF01, RN01, RN02, Cadastro N4 4a).

Os cenários do HTTP (status e corpo) ficam em `test_cadastro_endpoint.py`.
Aqui ficam a ordem das checagens, o que é gravado e a transação.
"""

import logging
from datetime import date
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.cadastro.apelido_resolver import (
    MENSAGEM_APELIDO_EM_USO,
    ApelidoIndisponivelError,
)
from apps.cadastro.cadastro_service import MENSAGEM_DADOS, CadastroService
from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.dados_cadastro import DadosCadastro
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
    campos = {
        "email_institucional": "251098732@aluno.unb.br",
        "apelido": "cris",
        "senha": "senha-forte-123",
        "aceite_privacidade": True,
    }
    return DadosCadastro(**{**campos, **extra})


def dados_professor(**extra):
    campos = {
        "email_institucional": "maria.silva@unb.br",
        "matricula_siape": "1234567",
        "senha": "senha-forte-123",
        "aceite_privacidade": True,
    }
    return DadosCadastro(**{**campos, **extra})


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
        dados_estudante(email_institucional="251098732@ALUNO.UNB.BR"),
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


# --- Corridas: o UNIQUE do banco decide --------------------------------------
#
# A checagem de duplicidade é simulada como "livre" (outro cadastro igual
# entrou entre a checagem e o INSERT). O INSERT bate no UNIQUE de verdade.

LIVRE = "apps.cadastro.conta_repository.ContaRepository"


def livre_na_primeira_consulta(metodo):
    """A primeira consulta diz "livre"; as seguintes consultam o banco."""
    original = getattr(ContaRepository, metodo)
    chamadas = []

    def consultar(self, *args):
        chamadas.append(args)
        return False if len(chamadas) == 1 else original(self, *args)

    return mock.patch(f"{LIVRE}.{metodo}", autospec=True, side_effect=consultar)


@pytest.mark.django_db
def test_duplo_envio_vira_ja_cadastrado_e_nao_apelido_em_uso(servico):
    """Duplo clique: o apelido "ocupado" é o da própria pessoa."""
    servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    with (
        livre_na_primeira_consulta("existe_matricula_ou_siape"),
        mock.patch(f"{LIVRE}.existe_email", side_effect=[False, True]),
        mock.patch(f"{LIVRE}.existe_apelido", return_value=False),
        pytest.raises(CadastroInvalidoError) as erro,
    ):
        servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    assert erro.value.mensagem == MENSAGEM_JA_CADASTRADO
    assert Usuario.objects.count() == 1


@pytest.mark.django_db
def test_corrida_no_apelido_digitado_vira_apelido_em_uso(servico):
    servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    with (
        livre_na_primeira_consulta("existe_apelido"),
        pytest.raises(CadastroInvalidoError) as erro,
    ):
        servico.registrar(
            TipoUsuario.ESTUDANTE,
            dados_estudante(email_institucional="251098733@aluno.unb.br"),
        )

    assert erro.value.mensagem == MENSAGEM_APELIDO_EM_USO


@pytest.mark.django_db
def test_corrida_no_apelido_extraido_vira_409_com_sugestao(servico):
    """O front só mostra o campo de apelido depois de um 409."""
    servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante(apelido="mariasilva"))

    with (
        livre_na_primeira_consulta("existe_apelido"),
        pytest.raises(ApelidoIndisponivelError) as erro,
    ):
        servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    assert erro.value.apelido_sugerido == "mariasilva1"


@pytest.mark.django_db
def test_integrity_error_desconhecido_nao_vira_ja_cadastrado(servico):
    """Bug de schema não pode aparecer ao usuário como "você já tem conta"."""
    with (
        mock.patch(
            "apps.gamificacao.pontuacao_service.PontuacaoService.inicializar_conta",
            side_effect=IntegrityError("NOT NULL"),
        ),
        pytest.raises(IntegrityError),
    ):
        servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())


@pytest.mark.django_db
def test_corrida_vai_para_o_log_sem_dados_pessoais(servico, caplog):
    """No MySQL, a mensagem do IntegrityError traz o valor repetido."""
    servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    with (
        caplog.at_level(logging.WARNING, logger="apps.cadastro.cadastro_service"),
        livre_na_primeira_consulta("existe_matricula_ou_siape"),
        mock.patch(f"{LIVRE}.existe_email", side_effect=[False, True]),
        mock.patch(f"{LIVRE}.existe_apelido", return_value=False),
        pytest.raises(CadastroInvalidoError),
    ):
        servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    mensagens = " ".join(r.getMessage() for r in caplog.records)
    assert "Corrida no cadastro" in mensagens
    assert "251098732" not in mensagens


@pytest.mark.django_db
def test_validation_error_do_model_vira_422_e_vai_para_o_log(servico, caplog):
    erro_do_model = ValidationError({"email_institucional": ["Muito longo."]})
    with (
        caplog.at_level(logging.WARNING, logger="apps.cadastro.cadastro_service"),
        mock.patch(
            "apps.cadastro.models.UsuarioManager.create_user",
            side_effect=erro_do_model,
        ),
        pytest.raises(CadastroInvalidoError) as erro,
    ):
        servico.registrar(TipoUsuario.ESTUDANTE, dados_estudante())

    assert erro.value.mensagem == MENSAGEM_DADOS
    assert any("email_institucional" in r.getMessage() for r in caplog.records)


# --- Ordem das checagens -----------------------------------------------------


@pytest.mark.django_db
def test_sem_aceite_e_rejeitado_antes_de_tudo(servico):
    with pytest.raises(CadastroInvalidoError) as erro:
        servico.registrar(
            TipoUsuario.ESTUDANTE,
            dados_estudante(aceite_privacidade=False, email_institucional="x"),
        )

    assert "aviso de privacidade" in erro.value.mensagem


@pytest.mark.django_db
def test_duplicidade_e_conferida_antes_do_apelido(servico):
    """Sem isso, o 409 do apelido diria que o e-mail ainda está livre."""
    servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    with pytest.raises(EmailJaCadastradoError):
        servico.registrar(
            TipoUsuario.PROFESSOR_SERVIDOR, dados_professor(matricula_siape="7654321")
        )


@pytest.mark.django_db
def test_matricula_repetida(servico):
    servico.registrar(TipoUsuario.PROFESSOR_SERVIDOR, dados_professor())

    with pytest.raises(IdentificadorJaCadastradoError):
        servico.registrar(
            TipoUsuario.PROFESSOR_SERVIDOR,
            dados_professor(email_institucional="outra@unb.br"),
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


@pytest.mark.django_db
def test_tipo_de_usuario_sem_regra_da_erro_claro(servico):
    with pytest.raises(ValueError, match="visitante"):
        servico.registrar("visitante", dados_estudante())


@pytest.mark.django_db
def test_senha_guardada_com_os_espacos_das_pontas(servico):
    conta = servico.registrar(
        TipoUsuario.ESTUDANTE, dados_estudante(senha="  abcdefg  ")
    )

    assert conta.check_password("  abcdefg  ")
    assert not conta.check_password("abcdefg")
