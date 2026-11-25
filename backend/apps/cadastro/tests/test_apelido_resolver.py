"""Regras do apelido (RN02, RF01.5, ADR 0002, Cadastro N4 4a)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cadastro.apelido_resolver import ApelidoIndisponivelError, ApelidoResolver
from apps.cadastro.erros import CadastroInvalidoError


def criar_conta(apelido, matricula="251098731"):
    return get_user_model().objects.create_user(
        matricula_siape=matricula,
        tipo_usuario="estudante",
        apelido=apelido,
        email_institucional=f"{matricula}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="2026-11-14",
        password="senha-forte-123",
    )


@pytest.fixture
def resolver():
    return ApelidoResolver()


# --- Apelido digitado (Estudante, ou Professor/Servidor depois do 409) -------


@pytest.mark.django_db
@pytest.mark.parametrize("valor", ["cris", "Zé_da.Silva-1", "abc", "a" * 20])
def test_apelido_digitado_valido_e_aceito(resolver, valor):
    assert resolver.resolver_manual(valor) == valor


@pytest.mark.django_db
def test_apelido_digitado_tira_espacos_das_pontas(resolver):
    assert resolver.resolver_manual("  cris  ") == "cris"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "valor",
    ["ab", "a" * 21, "com espaco", "", "emoji😀", "a\u200bb"],
)
def test_apelido_digitado_fora_das_regras_e_rejeitado(resolver, valor):
    with pytest.raises(CadastroInvalidoError) as erro:
        resolver.resolver_manual(valor)

    assert "3 a 20 caracteres" in erro.value.mensagem


@pytest.mark.django_db
@pytest.mark.parametrize("valor", ["Cris", "CRIS", "crís"])
def test_apelido_digitado_em_uso_sem_distinguir_maiusculas_e_acento(resolver, valor):
    criar_conta("cris")

    with pytest.raises(CadastroInvalidoError) as erro:
        resolver.resolver_manual(valor)

    assert erro.value.mensagem == "Este apelido já está em uso. Escolha outro."
    # Não é o erro recuperável: esse é só para o apelido extraído.
    assert not isinstance(erro.value, ApelidoIndisponivelError)


# --- Apelido extraído do e-mail (Professor/Servidor) -------------------------


@pytest.mark.django_db
def test_apelido_extraido_tira_caracteres_nao_alfanumericos(resolver):
    """RF01.4: maria.silva@unb.br vira o apelido `mariasilva`."""
    assert resolver.resolver_extraido("maria.silva") == "mariasilva"


@pytest.mark.django_db
def test_apelido_extraido_aceita_qualquer_texto_antes_do_arroba(resolver):
    assert resolver.resolver_extraido("j.o-a_o+2") == "joao2"


@pytest.mark.django_db
def test_apelido_extraido_em_uso_e_recuperavel_com_sugestao_livre(resolver):
    criar_conta("mariasilva")
    criar_conta("mariasilva1", matricula="251098734")

    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("maria.silva")

    assert erro.value.apelido_sugerido == "mariasilva2"
    assert "mariasilva" in erro.value.mensagem


@pytest.mark.django_db
def test_apelido_extraido_curto_demais_pede_apelido_digitado(resolver):
    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("a.b")

    # Completa até 3 caracteres antes de numerar, como o simulado do front.
    assert erro.value.apelido_sugerido == "ab01"


@pytest.mark.django_db
def test_apelido_extraido_longo_demais_pede_apelido_digitado(resolver):
    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("maria.aparecida.dos.santos")

    sugestao = erro.value.apelido_sugerido
    assert sugestao == "mariaaparecidadoss1"
    assert len(sugestao) <= 20


@pytest.mark.django_db
def test_apelido_extraido_vazio_depois_da_limpeza(resolver):
    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("...")

    assert erro.value.apelido_sugerido == "0001"


@pytest.mark.django_db
def test_sugestao_nunca_passa_de_20_caracteres(resolver):
    raiz = "a" * 18
    for n in range(1, 10):
        criar_conta(f"{raiz}{n}", matricula=f"25109{n:04d}")

    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("a" * 25)

    assert erro.value.apelido_sugerido == "a" * 18 + "10"


# --- validar_disponibilidade -------------------------------------------------


@pytest.mark.django_db
def test_validar_disponibilidade(resolver):
    criar_conta("cris")

    assert not resolver.validar_disponibilidade("CRIS")
    assert resolver.validar_disponibilidade("outro")


@pytest.mark.django_db
def test_mensagem_do_409_nao_repete_texto_longo(resolver):
    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("a" * 250)

    assert "a" * 21 not in erro.value.mensagem


@pytest.mark.django_db
def test_mensagem_do_409_sem_texto_aproveitavel(resolver):
    with pytest.raises(ApelidoIndisponivelError) as erro:
        resolver.resolver_extraido("--")

    assert '""' not in erro.value.mensagem
    assert "a partir do seu e-mail" in erro.value.mensagem


@pytest.mark.django_db
def test_sugestao_usa_uma_consulta_so(resolver, django_assert_max_num_queries):
    for n in range(1, 31):
        criar_conta(f"mariasilva{n}", matricula=f"25109{n:04d}")
    criar_conta("mariasilva", matricula="251098799")

    # Uma consulta para ver que "mariasilva" está em uso e outra para a sugestão.
    with (
        django_assert_max_num_queries(2),
        pytest.raises(ApelidoIndisponivelError) as erro,
    ):
        resolver.resolver_extraido("maria.silva")

    assert erro.value.apelido_sugerido == "mariasilva31"
