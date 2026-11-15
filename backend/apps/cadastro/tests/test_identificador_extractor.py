"""Estratégia de extração por tipo de usuário (ADR 0002, Cadastro N4 4a)."""

import pytest

from apps.cadastro.dados_cadastro import DadosCadastro
from apps.cadastro.identificador_extractor import (
    EstudanteIdentificadorExtractor,
    IdentificadorExtractor,
    IdentificadorExtraido,
    ProfessorServidorIdentificadorExtractor,
    extractor_para,
)
from apps.cadastro.models import TipoUsuario


def dados(**campos):
    return DadosCadastro(senha="senha-forte-123", aceite_privacidade=True, **campos)


def test_estudante_tira_a_matricula_do_email_e_nao_sugere_apelido():
    """Estudante: a matrícula vem do e-mail e o apelido é digitado."""
    extraido = EstudanteIdentificadorExtractor().extrair(
        dados(email_institucional=" 251098732@aluno.unb.br ", apelido="cris")
    )

    assert extraido == IdentificadorExtraido(
        identificador="251098732", apelido_sugerido=None
    )


def test_estudante_ignora_matricula_digitada():
    extraido = EstudanteIdentificadorExtractor().extrair(
        dados(email_institucional="251098732@aluno.unb.br", matricula_siape="999999999")
    )

    assert extraido.identificador == "251098732"


def test_professor_servidor_usa_o_siape_digitado_e_sugere_o_texto_antes_do_arroba():
    """Professor/Servidor: o SIAPE é digitado e o apelido vem do e-mail."""
    extraido = ProfessorServidorIdentificadorExtractor().extrair(
        dados(email_institucional="maria.silva@unb.br", matricula_siape=" 1234567 ")
    )

    # A limpeza dos caracteres é do ApelidoResolver, não do extractor.
    assert extraido == IdentificadorExtraido(
        identificador="1234567", apelido_sugerido="maria.silva"
    )


def test_professor_servidor_sem_siape_extrai_identificador_vazio():
    extraido = ProfessorServidorIdentificadorExtractor().extrair(
        dados(email_institucional="maria@unb.br")
    )

    assert extraido.identificador == ""


@pytest.mark.parametrize(
    ("tipo", "classe"),
    [
        (TipoUsuario.ESTUDANTE, EstudanteIdentificadorExtractor),
        (TipoUsuario.PROFESSOR_SERVIDOR, ProfessorServidorIdentificadorExtractor),
    ],
)
def test_estrategia_escolhida_pelo_tipo_de_usuario(tipo, classe):
    extractor = extractor_para(tipo)

    assert isinstance(extractor, classe)
    assert isinstance(extractor, IdentificadorExtractor)


def test_tipo_sem_estrategia_da_erro_claro():
    with pytest.raises(ValueError, match="visitante"):
        extractor_para("visitante")
