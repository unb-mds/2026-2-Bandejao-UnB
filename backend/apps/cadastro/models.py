"""Models do app `cadastro`: USUARIO e TOKEN.

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(dicionário de dados), ADR 0007 (sessão), ADR 0008 (matrícula em texto claro).
"""

import unicodedata

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


def normalizar_apelido(apelido: str) -> str:
    """Remove acentos e passa para minúsculas.

    Garante a unicidade do apelido de forma idêntica em SQLite e MySQL
    (N4 banco, estratégia de migração, item 2).
    """
    decomposto = unicodedata.normalize("NFKD", apelido)
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acentos.lower()


class TipoUsuario(models.TextChoices):
    ESTUDANTE = "estudante", "Estudante"
    PROFESSOR_SERVIDOR = "professor_servidor", "Professor/Servidor"


class StatusUsuario(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    ATIVO = "ativo", "Ativo"
    SUSPENSO = "suspenso", "Suspenso"
    REMOVIDO = "removido", "Removido"


class TipoToken(models.TextChoices):
    CONFIRMACAO_EMAIL = "confirmacao_email", "Confirmação de e-mail"
    REDEFINICAO_SENHA = "redefinicao_senha", "Redefinição de senha"


validador_apelido = RegexValidator(
    regex=r"^\S{3,20}$",
    message="O apelido deve ter de 3 a 20 caracteres, sem espaço.",
)


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, matricula_siape, password=None, **extra_fields):
        if not matricula_siape:
            raise ValueError("A matrícula/SIAPE é obrigatória.")
        extra_fields.setdefault("aceite_privacidade_em", timezone.now())
        usuario = self.model(matricula_siape=matricula_siape, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario


class Usuario(AbstractBaseUser):
    """Conta de acesso ao aplicativo (glossário: "Usuário")."""

    tipo_usuario = models.CharField(max_length=20, choices=TipoUsuario.choices)
    # Dado privado (RI10, RNF07): nunca em resposta pública. Texto claro (ADR 0008).
    matricula_siape = models.CharField(max_length=9, unique=True)
    apelido = models.CharField(max_length=20, validators=[validador_apelido])
    # Gerado no save(); garante unicidade sem depender da collation do banco.
    apelido_normalizado = models.CharField(
        max_length=20, unique=True, editable=False
    )
    email_institucional = models.EmailField(unique=True)
    # Substitui o campo `password` do Django; a coluna se chama `senha_hash`
    # como no Nível 4. O hash é feito por set_password(), nunca texto plano.
    password = models.CharField("senha_hash", max_length=128, db_column="senha_hash")
    email_confirmado = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=StatusUsuario.choices,
        default=StatusUsuario.PENDENTE,
    )
    aceite_privacidade_em = models.DateTimeField()
    versao_aviso_aceita = models.CharField(max_length=20)
    criado_em = models.DateTimeField(auto_now_add=True)
    tentativas_login_falhas = models.IntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    removido_em = models.DateTimeField(null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "matricula_siape"
    REQUIRED_FIELDS = ["tipo_usuario", "apelido", "email_institucional"]

    @property
    def is_active(self):
        """Conta suspensa ou removida não autentica (ADR 0007, ADR 0004)."""
        return self.status not in (StatusUsuario.SUSPENSO, StatusUsuario.REMOVIDO)

    def save(self, *args, **kwargs):
        self.apelido_normalizado = normalizar_apelido(self.apelido)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.apelido


class Token(models.Model):
    """Link de uso único para confirmação de e-mail e redefinição de senha."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    tipo = models.CharField(max_length=20, choices=TipoToken.choices)
    # SHA-256 do token enviado por e-mail; o token em claro nunca é guardado.
    token_hash = models.CharField(max_length=64, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()
    usado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tipo} de {self.usuario_id}"
