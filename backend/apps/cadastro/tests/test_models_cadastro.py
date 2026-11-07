"""Testes dos models USUARIO e TOKEN (BD-01, app `cadastro`).

Cada teste vem de uma regra do Nível 4 do banco (dicionário de dados e
tabela "Constraints principais").
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
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
        "versao_aviso_aceita": "teste",
    }
    dados.update(kwargs)
    senha = dados.pop("password", "Senha-forte-123")
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


class TestUsuario:
    def test_modelo_de_usuario_do_projeto_e_o_do_cadastro(self):
        # Falha se AUTH_USER_MODEL não for "cadastro.Usuario" nas settings.
        assert get_user_model() is Usuario

    def test_matricula_siape_deve_ser_unica(self):
        primeiro = criar_usuario()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                criar_usuario(matricula_siape=primeiro.matricula_siape)

    def test_email_institucional_deve_ser_unico(self):
        primeiro = criar_usuario()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                criar_usuario(email_institucional=primeiro.email_institucional)

    def test_apelido_unico_sem_distinguir_maiusculas(self):
        criar_usuario(apelido="Ana")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                criar_usuario(apelido="ana")

    def test_apelido_unico_sem_distinguir_acentos(self):
        criar_usuario(apelido="José")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                criar_usuario(apelido="Jose")

    def test_apelido_normalizado_e_gravado_no_save(self):
        usuario = criar_usuario(apelido="JoãoÁgil")
        usuario.refresh_from_db()
        assert usuario.apelido_normalizado == "joaoagil"

    @pytest.mark.parametrize(
        "apelido, esperado",
        [("Ana", "ana"), ("José", "jose"), ("ÇaÕ", "cao"), ("abc123", "abc123")],
    )
    def test_normalizar_apelido(self, apelido, esperado):
        assert normalizar_apelido(apelido) == esperado

    @pytest.mark.parametrize("apelido", ["ab", "a b", "a" * 21, "com espaco"])
    def test_apelido_invalido_e_rejeitado(self, apelido):
        campo = Usuario._meta.get_field("apelido")
        with pytest.raises(ValidationError):
            campo.clean(apelido, None)

    @pytest.mark.parametrize("apelido", ["abc", "José", "a" * 20])
    def test_apelido_valido_e_aceito(self, apelido):
        campo = Usuario._meta.get_field("apelido")
        assert campo.clean(apelido, None) == apelido

    def test_conta_nasce_pendente_e_sem_email_confirmado(self):
        usuario = criar_usuario()
        assert usuario.status == StatusUsuario.PENDENTE
        assert usuario.email_confirmado is False
        assert usuario.tentativas_login_falhas == 0
        assert usuario.bloqueado_ate is None
        assert usuario.removido_em is None

    def test_senha_nunca_e_guardada_em_texto_plano(self):
        usuario = criar_usuario(password="Senha-forte-123")
        usuario.refresh_from_db()
        assert usuario.password != "Senha-forte-123"
        assert usuario.check_password("Senha-forte-123")

    @pytest.mark.parametrize(
        "status, ativo",
        [
            (StatusUsuario.PENDENTE, True),
            (StatusUsuario.ATIVO, True),
            (StatusUsuario.SUSPENSO, False),
            (StatusUsuario.REMOVIDO, False),
        ],
    )
    def test_conta_suspensa_ou_removida_nao_autentica(self, status, ativo):
        usuario = criar_usuario(status=status)
        assert usuario.is_active is ativo


class TestToken:
    def test_token_hash_deve_ser_unico(self):
        usuario = criar_usuario()
        criar_token(usuario, token_hash="b" * 64)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
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
