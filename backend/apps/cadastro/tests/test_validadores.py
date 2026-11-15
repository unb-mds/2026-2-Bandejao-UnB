"""Regras de formato do cadastro (RN01, RF01.1 a RF01.4, Cadastro N4 4a)."""

from datetime import date

import pytest

from apps.cadastro.validadores import (
    EmailInstitucionalValidator,
    MatriculaValidator,
    SenhaValidator,
    SiapeValidator,
)

# 2º semestre de 2026: o último prefixo aceito é 262 (Anexo A).
HOJE = date(2026, 11, 14)


@pytest.fixture
def matricula():
    return MatriculaValidator(hoje=HOJE)


# --- MatriculaValidator.validar_formato: exatamente 9 dígitos -----------------


@pytest.mark.parametrize("valor", ["251098732", "000000000"])
def test_matricula_com_9_digitos_tem_formato_valido(matricula, valor):
    assert matricula.validar_formato(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "25109873",  # 8 dígitos, anterior a 2010 (L10)
        "2510987321",  # 10 dígitos
        "25109873a",  # letra
        "251.098.732",  # pontuação
        "251098732\n",  # quebra de linha no fim
        "２５１０９８７３２",  # dígitos de largura total (não ASCII)
        "",
    ],
)
def test_matricula_fora_do_formato_e_rejeitada(matricula, valor):
    assert not matricula.validar_formato(valor)


# --- MatriculaValidator.validar_prefixo_ano_semestre (RN01, Anexo A) ---------


@pytest.mark.parametrize("valor", ["101098732", "102098732", "251098732", "262098732"])
def test_prefixo_entre_101_e_o_semestre_corrente_e_aceito(matricula, valor):
    assert matricula.validar_prefixo_ano_semestre(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "091098732",  # 2009: antes da janela
        "100098732",  # 3º dígito 0
        "253098732",  # 3º dígito 3
        "271098732",  # 1º semestre de 2027: "futuro"
        "999098732",
    ],
)
def test_prefixo_fora_da_janela_e_rejeitado(matricula, valor):
    assert not matricula.validar_prefixo_ano_semestre(valor)


def test_no_1o_semestre_o_prefixo_do_2o_ainda_e_futuro():
    validador = MatriculaValidator(hoje=date(2026, 6, 30))

    assert validador.validar_prefixo_ano_semestre("261098732")
    assert not validador.validar_prefixo_ano_semestre("262098732")


def test_virada_de_semestre_aceita_o_novo_prefixo_sem_mudar_codigo():
    """RF01.3: o intervalo é recalculado a partir da data."""
    validador = MatriculaValidator(hoje=date(2027, 1, 1))

    assert validador.validar_prefixo_ano_semestre("271098732")
    assert not validador.validar_prefixo_ano_semestre("272098732")


def test_sem_data_usa_o_dia_de_hoje():
    ano = date.today().year % 100
    prefixo_futuro = f"{ano + 1:02d}1"

    assert not MatriculaValidator().validar_prefixo_ano_semestre(
        f"{prefixo_futuro}098732"
    )


# --- MatriculaValidator.validar_sequencia_digitos (RN01) ---------------------


@pytest.mark.parametrize("valor", ["251098732", "251567890", "251112233", "251123457"])
def test_seis_digitos_finais_sem_sequencia_obvia_sao_aceitos(matricula, valor):
    assert matricula.validar_sequencia_digitos(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "251123456",  # crescente
        "251456789",  # crescente
        "251654321",  # decrescente
        "251987654",  # decrescente
        "251111111",  # todos iguais
        "251000000",  # todos iguais
    ],
)
def test_seis_digitos_finais_em_sequencia_obvia_sao_rejeitados(matricula, valor):
    assert not matricula.validar_sequencia_digitos(valor)


# --- SiapeValidator (RN01, RF01.4) -------------------------------------------


def test_siape_com_7_digitos_e_valido():
    assert SiapeValidator().validar_formato("1234567")


@pytest.mark.parametrize("valor", ["123456", "12345678", "123456a", "123.4567", ""])
def test_siape_fora_de_7_digitos_e_rejeitado(valor):
    assert not SiapeValidator().validar_formato(valor)


# --- EmailInstitucionalValidator (RF01.2, RF01.4, ADR 0002) ------------------


@pytest.mark.parametrize(
    "valor", ["251098732@aluno.unb.br", "251098732@ALUNO.UNB.BR", "abc@aluno.unb.br"]
)
def test_email_de_estudante_no_dominio_aluno_unb(valor):
    # A parte antes do "@" é conferida depois, como matrícula (RN01).
    assert EmailInstitucionalValidator().validar_formato_estudante(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "251098732@unb.br",
        "251098732@aluno.unb.br.com",
        "251098732@xaluno.unb.br",
        "@aluno.unb.br",
        "a b@aluno.unb.br",
        "a@b@aluno.unb.br",
        "251098732@aluno.unb.br\n",
    ],
)
def test_email_de_estudante_fora_do_formato_e_rejeitado(valor):
    assert not EmailInstitucionalValidator().validar_formato_estudante(valor)


@pytest.mark.parametrize(
    "valor", ["maria.silva@unb.br", "MARIA@UNB.BR", "joao_2@unb.br"]
)
def test_email_de_professor_servidor_no_dominio_unb(valor):
    assert EmailInstitucionalValidator().validar_formato_professor_servidor(valor)


@pytest.mark.parametrize(
    "valor",
    ["maria@aluno.unb.br", "maria@gmail.com", "maria@unb.br.com", "@unb.br", "maria"],
)
def test_email_de_professor_servidor_fora_do_dominio_e_rejeitado(valor):
    assert not EmailInstitucionalValidator().validar_formato_professor_servidor(valor)


# --- SenhaValidator (RF01.1) ---------------------------------------------------


@pytest.mark.parametrize("valor", ["12345678", "senha-forte-123"])
def test_senha_com_8_caracteres_ou_mais_e_valida(valor):
    assert SenhaValidator().validar(valor)


@pytest.mark.parametrize("valor", ["1234567", ""])
def test_senha_com_menos_de_8_caracteres_e_rejeitada(valor):
    assert not SenhaValidator().validar(valor)
