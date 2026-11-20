"""Serializers de entrada do cadastro e do login (BE-05)."""

from apps.cadastro.serializers import (
    CadastroEntradaSerializer,
    LoginEntradaSerializer,
    ReenvioConfirmacaoEntradaSerializer,
)


def test_login_mantem_os_espacos_das_pontas_da_senha():
    """Mesma regra do cadastro: senão a conta criada com espaços não entra."""
    entrada = LoginEntradaSerializer(
        data={"emailInstitucional": "maria.silva@unb.br", "senha": "  a  "}
    )

    assert entrada.is_valid()
    assert entrada.validated_data["senha"] == "  a  "


def test_login_nao_aceita_mais_a_matricula_siape():
    """BE-20: o login é pelo e-mail institucional; o campo antigo não serve."""
    entrada = LoginEntradaSerializer(
        data={"matriculaSiape": "202400001", "senha": "senha-forte-123"}
    )

    assert not entrada.is_valid()
    assert "emailInstitucional" in entrada.errors


def test_reenvio_com_email_e_token_juntos_mantem_os_dois():
    """Quem escolhe a prioridade (vale o e-mail) é o service."""
    entrada = ReenvioConfirmacaoEntradaSerializer(
        data={"emailInstitucional": "202400001@aluno.unb.br", "token": "abc"}
    )

    assert entrada.is_valid(), entrada.errors
    assert entrada.validated_data == {
        "emailInstitucional": "202400001@aluno.unb.br",
        "token": "abc",
    }


def test_cadastro_vira_dados_cadastro_sem_o_camel_case_da_api():
    entrada = CadastroEntradaSerializer(
        data={
            "tipoUsuario": "professor_servidor",
            "emailInstitucional": "maria.silva@unb.br",
            "senha": "senha-forte-123",
            "apelido": None,
            "matriculaSiape": "1234567",
            "aceitePrivacidade": True,
        }
    )

    assert entrada.is_valid(), entrada.errors
    dados = entrada.para_dados_cadastro()
    assert dados.email_institucional == "maria.silva@unb.br"
    assert dados.matricula_siape == "1234567"
    assert dados.apelido == ""
    assert dados.aceite_privacidade is True
