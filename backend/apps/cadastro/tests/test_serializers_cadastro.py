"""Serializers de entrada do cadastro e do login (BE-05)."""

from apps.cadastro.serializers import CadastroEntradaSerializer, LoginEntradaSerializer


def test_login_mantem_os_espacos_das_pontas_da_senha():
    """Mesma regra do cadastro: senão a conta criada com espaços não entra."""
    entrada = LoginEntradaSerializer(
        data={"matriculaSiape": "1234567", "senha": "  a  "}
    )

    assert entrada.is_valid()
    assert entrada.validated_data["senha"] == "  a  "


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
