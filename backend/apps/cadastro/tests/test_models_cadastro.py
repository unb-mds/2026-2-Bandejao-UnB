"""Testes dos models USUARIO e TOKEN (BD-01, app `cadastro`).

Cada teste vem de uma regra do Nível 4 do banco (dicionário de dados e
tabela "Constraints principais") ou de um ponto do review do PR #107.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cadastro.models import (
    StatusUsuario,
    TipoToken,
    TipoUsuario,
    Token,
    Usuario,
    normalizar_apelido,
)

pytestmark = pytest.mark.django_db

SENHA = "Senha-forte-123"
_contador = 0


def criar_usuario(**kwargs):
    """Cria um usuário válido, com valores únicos a cada chamada."""
    global _contador
    _contador += 1
    n = _contador
    dados = {
        "tipo_usuario": TipoUsuario.ESTUDANTE,
        "matricula_siape": f"{n:09d}",
        "apelido": f"apelido{n}",
        "email_institucional": f"{n:09d}@aluno.unb.br",
        "aceite_privacidade_em": timezone.now(),
        "versao_aviso_aceita": "teste",
    }
    dados.update(kwargs)
    senha = dados.pop("password", SENHA)
    return Usuario.objects.create_user(password=senha, **dados)


def criar_token(usuario, **kwargs):
    dados = {
        "usuario": usuario,
        "tipo": TipoToken.CONFIRMACAO_EMAIL,
        "token_hash": "a" * 64,
        "expira_em": timezone.now() + timedelta(hours=24),
    }
    dados.update(kwargs)
    return Token.objects.create(**dados)


class TestUnicidade:
    def test_modelo_de_usuario_do_projeto_e_o_do_cadastro(self):
        # Falha se AUTH_USER_MODEL não for "cadastro.Usuario" nas settings.
        assert get_user_model() is Usuario

    def test_matricula_siape_deve_ser_unica(self):
        primeiro = criar_usuario()
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(matricula_siape=primeiro.matricula_siape)

    def test_email_institucional_deve_ser_unico(self):
        primeiro = criar_usuario()
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(email_institucional=primeiro.email_institucional)

    def test_email_e_gravado_em_minusculas(self):
        usuario = criar_usuario(email_institucional="Fulano@Aluno.UnB.br")
        usuario.refresh_from_db()
        assert usuario.email_institucional == "fulano@aluno.unb.br"

    def test_email_unico_sem_distinguir_maiusculas(self):
        criar_usuario(email_institucional="Maria@aluno.unb.br")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(email_institucional="maria@ALUNO.unb.br")

    def test_apelido_unico_sem_distinguir_maiusculas(self):
        criar_usuario(apelido="Ana")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(apelido="ana")

    def test_apelido_unico_sem_distinguir_acentos(self):
        criar_usuario(apelido="José")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(apelido="Jose")

    def test_apelido_unico_com_eszett(self):
        # "ß" e "ss" colidem no MySQL; aqui colidem nos dois bancos.
        criar_usuario(apelido="Straße")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(apelido="Strasse")

    def test_apelido_normalizado_e_gravado_no_save(self):
        usuario = criar_usuario(apelido="JoãoÁgil")
        usuario.refresh_from_db()
        assert usuario.apelido_normalizado == "joaoagil"

    def test_save_com_update_fields_atualiza_o_apelido_normalizado(self):
        usuario = criar_usuario(apelido="Ana")
        usuario.apelido = "Bia"
        usuario.save(update_fields=["apelido"])
        usuario.refresh_from_db()
        assert usuario.apelido_normalizado == "bia"
        # "Ana" ficou livre e "Bia" continua protegido.
        criar_usuario(apelido="Ana")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(apelido="bia")


class TestApelido:
    @pytest.mark.parametrize(
        "apelido, esperado",
        [
            ("Ana", "ana"),
            ("José", "jose"),
            ("ÇaÕ", "cao"),
            ("abc123", "abc123"),
            ("Straße", "strasse"),
            ("İsmail", "ismail"),
        ],
    )
    def test_normalizar_apelido(self, apelido, esperado):
        assert normalizar_apelido(apelido) == esperado

    @pytest.mark.parametrize(
        "apelido",
        [
            "ab",  # curto demais
            "a b",  # espaço
            "com espaco",
            "a" * 21,  # longo demais
            "ﬃ" * 20,  # ligadura: normaliza para 60 caracteres
            "\u0301\u0301\u0301",  # só acentos soltos: normaliza para vazio
            "ana\u200b",  # espaço de largura zero (invisível)
            "Søren",  # "ø" não tem equivalente ASCII
            "abc\n",  # quebra de linha no fim
            "a@b",
        ],
    )
    def test_apelido_invalido_e_rejeitado(self, apelido):
        campo = Usuario._meta.get_field("apelido")
        with pytest.raises(ValidationError):
            campo.clean(apelido, None)

    @pytest.mark.parametrize(
        "apelido",
        ["abc", "José", "a" * 20, "ana.silva", "ana_silva-2", "Straße"],
    )
    def test_apelido_valido_e_aceito(self, apelido):
        campo = Usuario._meta.get_field("apelido")
        assert campo.clean(apelido, None) == apelido

    def test_create_user_rejeita_apelido_invalido(self):
        with pytest.raises(ValidationError):
            criar_usuario(apelido="a b")

    def test_apelido_decomposto_e_gravado_composto(self):
        # "e" + acento combinado (NFD) vira "é" (NFC) antes de validar e salvar.
        usuario = criar_usuario(apelido="Jose\u0301")
        usuario.refresh_from_db()
        assert usuario.apelido == "Jos\u00e9"
        assert usuario.apelido_normalizado == "jose"

    def test_apelido_decomposto_colide_com_o_composto(self):
        criar_usuario(apelido="Jos\u00e9")
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_usuario(apelido="Jose\u0301")


class TestCriacaoDeConta:
    def test_conta_nasce_pendente_e_sem_email_confirmado(self):
        usuario = criar_usuario()
        assert usuario.status == StatusUsuario.PENDENTE
        assert usuario.email_confirmado is False
        assert usuario.tentativas_login_falhas == 0
        assert usuario.bloqueado_ate is None
        assert usuario.removido_em is None

    def test_senha_nunca_e_guardada_em_texto_plano(self):
        usuario = criar_usuario(password=SENHA)
        usuario.refresh_from_db()
        assert usuario.password != SENHA
        assert usuario.check_password(SENHA)

    def test_senha_errada_nao_confere(self):
        usuario = criar_usuario(password=SENHA)
        assert usuario.check_password("errada") is False

    def test_matricula_vazia_e_rejeitada(self):
        with pytest.raises(ValueError):
            criar_usuario(matricula_siape="")

    def test_aceite_de_privacidade_e_obrigatorio(self):
        with pytest.raises(ValueError):
            criar_usuario(aceite_privacidade_em=None)

    def test_versao_do_aviso_e_obrigatoria(self):
        with pytest.raises(ValueError):
            criar_usuario(versao_aviso_aceita="")

    def test_tipo_de_usuario_invalido_e_rejeitado(self):
        with pytest.raises(ValidationError):
            criar_usuario(tipo_usuario="admin")

    @pytest.mark.parametrize(
        "matricula",
        ["12345678", "1234567890", "12345678a", "١٢٣٤٥٦٧٨٩"],
    )
    def test_estudante_exige_matricula_de_9_digitos(self, matricula):
        with pytest.raises(ValidationError):
            criar_usuario(matricula_siape=matricula)

    def test_professor_servidor_aceita_siape_de_7_digitos(self):
        usuario = criar_usuario(
            tipo_usuario=TipoUsuario.PROFESSOR_SERVIDOR,
            matricula_siape="1234567",
        )
        assert usuario.matricula_siape == "1234567"

    def test_professor_servidor_rejeita_9_digitos(self):
        with pytest.raises(ValidationError):
            criar_usuario(
                tipo_usuario=TipoUsuario.PROFESSOR_SERVIDOR,
                matricula_siape="123456789",
            )


class TestStatus:
    @pytest.mark.parametrize(
        "status, ativo",
        [
            (StatusUsuario.PENDENTE, True),
            (StatusUsuario.ATIVO, True),
            (StatusUsuario.SUSPENSO, False),
            (StatusUsuario.REMOVIDO, False),
        ],
    )
    def test_suspenso_e_removido_ficam_inativos(self, status, ativo):
        usuario = criar_usuario(status=status)
        assert usuario.is_active is ativo

    @pytest.mark.parametrize(
        "status, autentica",
        [
            (StatusUsuario.PENDENTE, True),
            (StatusUsuario.ATIVO, True),
            (StatusUsuario.SUSPENSO, False),
            (StatusUsuario.REMOVIDO, False),
        ],
    )
    def test_conta_suspensa_ou_removida_nao_autentica(self, status, autentica):
        usuario = criar_usuario(status=status)
        autenticado = authenticate(username=usuario.matricula_siape, password=SENHA)
        assert (autenticado is not None) is autentica


class TestToken:
    def test_token_hash_deve_ser_unico(self):
        usuario = criar_usuario()
        criar_token(usuario, token_hash="b" * 64)
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_token(usuario, token_hash="b" * 64)

    def test_token_novo_nao_foi_usado(self):
        token = criar_token(criar_usuario())
        assert token.usado_em is None

    def test_tokens_somem_junto_com_o_usuario(self):
        usuario = criar_usuario()
        criar_token(usuario)
        usuario.delete()
        assert Token.objects.count() == 0

    def test_usuario_acessa_seus_tokens(self):
        usuario = criar_usuario()
        token = criar_token(usuario, tipo=TipoToken.REDEFINICAO_SENHA)
        assert list(usuario.tokens.all()) == [token]
