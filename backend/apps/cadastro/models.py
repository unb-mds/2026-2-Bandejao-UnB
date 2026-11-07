"""Models do app `cadastro`: USUARIO e TOKEN.

Fonte: docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md
(dicionário de dados), ADR 0007 (sessão), ADR 0008 (matrícula em texto claro).
"""

import re
import unicodedata

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

# Apelido digitado: de 3 a 20 caracteres, só letras, números, ponto, hífen e
# sublinhado (sem espaço nem caractere invisível). `fullmatch` evita o `$`, que
# aceitaria uma quebra de linha no fim.
FORMATO_APELIDO = re.compile(r"[\w.-]{3,20}")
# Apelido depois de normalizado: ASCII minúsculo, de 3 a 20 caracteres.
FORMATO_APELIDO_NORMALIZADO = re.compile(r"[a-z0-9._-]{3,20}")
MENSAGEM_APELIDO = (
    "O apelido deve ter de 3 a 20 caracteres: letras (com ou sem acento), "
    "números, ponto, hífen ou sublinhado, sem espaço."
)


def normalizar_apelido(apelido: str) -> str:
    """Remove acentos e diferenças de maiúsculas/minúsculas.

    NFKD separa as letras dos acentos (e expande ligaduras); `casefold` trata
    casos como "ß" -> "ss"; o segundo NFKD cobre o que o `casefold` produz.
    """
    texto = unicodedata.normalize("NFKD", apelido).casefold()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def validar_apelido(valor: str) -> None:
    """Valida o apelido digitado e também o resultado da normalização.

    Como o apelido normalizado só pode ter `[a-z0-9._-]`, a comparação do
    UNIQUE dá o mesmo resultado em SQLite e MySQL, qualquer que seja a
    collation da coluna. Isso barra ligaduras que viram mais de 20 caracteres,
    apelidos que normalizam para vazio, letras como "ø" (sem equivalente
    ASCII) e caracteres invisíveis.
    """
    if not FORMATO_APELIDO.fullmatch(valor):
        raise ValidationError(MENSAGEM_APELIDO, code="apelido_invalido")
    if not FORMATO_APELIDO_NORMALIZADO.fullmatch(normalizar_apelido(valor)):
        raise ValidationError(MENSAGEM_APELIDO, code="apelido_invalido")


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


class UsuarioManager(BaseUserManager):
    """Gerenciador de `Usuario`.

    Não há `create_superuser` nem `is_staff`: o admin do Django não é usado,
    porque a moderação é feita por acesso direto ao banco (ADR 0004, RNF08).
    """

    use_in_migrations = True

    def create_user(self, matricula_siape, password=None, **extra_fields):
        if not matricula_siape:
            raise ValueError("A matrícula/SIAPE é obrigatória.")
        # O aceite do aviso de privacidade é a prova do consentimento (RF11,
        # RNF07.1): quem cria a conta precisa informá-lo, nunca é presumido.
        for campo in ("aceite_privacidade_em", "versao_aviso_aceita"):
            if not extra_fields.get(campo):
                raise ValueError(
                    f"`{campo}` é obrigatório: registra o consentimento real "
                    "da pessoa (RF11, RNF07.1)."
                )
        usuario = self.model(matricula_siape=matricula_siape, **extra_fields)
        usuario.set_password(password)
        # Valida formato, choices e campos obrigatórios. A unicidade fica por
        # conta do banco (IntegrityError), que é a defesa que vale de verdade.
        usuario.full_clean(
            exclude=["password"],
            validate_unique=False,
            validate_constraints=False,
        )
        usuario.save(using=self._db)
        return usuario


class Usuario(AbstractBaseUser):
    """Conta de acesso ao aplicativo (glossário: "Usuário")."""

    tipo_usuario = models.CharField(max_length=20, choices=TipoUsuario.choices)
    # Dado privado (RI10, RNF07): nunca em resposta pública. Texto claro (ADR 0008).
    matricula_siape = models.CharField(max_length=9, unique=True)
    apelido = models.CharField(max_length=20, validators=[validar_apelido])
    # Gerado no save(). Só tem [a-z0-9._-] (garantido por `validar_apelido`),
    # então a collation do banco não muda o resultado do UNIQUE. Atenção:
    # QuerySet.update() e bulk_create() não passam pelo save().
    apelido_normalizado = models.CharField(max_length=20, unique=True, editable=False)
    # Gravado sempre em minúsculas (save), para o UNIQUE ser igual nos dois bancos.
    email_institucional = models.EmailField(unique=True)
    # Coluna `senha_hash` do Nível 4. Grave sempre por set_password() ou
    # create_user(): `Usuario.objects.create(password="x")` gravaria texto plano.
    password = models.CharField("senha", max_length=128, db_column="senha_hash")
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
    REQUIRED_FIELDS = ("tipo_usuario", "apelido", "email_institucional")

    @property
    def is_active(self):
        """Conta suspensa ou removida não autentica (ADR 0007, ADR 0004).

        A conta `pendente` continua "ativa" para o Django de propósito: quem
        barra o login dela é o LoginService (conta não confirmada, RF02/RF03).
        """
        return self.status not in (StatusUsuario.SUSPENSO, StatusUsuario.REMOVIDO)

    def clean(self):
        super().clean()
        # 9 dígitos para estudante (extraída do e-mail) e 7 para
        # professor/servidor (digitada), conforme o dicionário de dados.
        if self.tipo_usuario == TipoUsuario.ESTUDANTE:
            tamanho = 9
        elif self.tipo_usuario == TipoUsuario.PROFESSOR_SERVIDOR:
            tamanho = 7
        else:
            return
        if not re.fullmatch(rf"[0-9]{{{tamanho}}}", self.matricula_siape or ""):
            raise ValidationError(
                {"matricula_siape": f"A matrícula/SIAPE deve ter {tamanho} dígitos."}
            )

    def save(self, *args, **kwargs):
        self.apelido_normalizado = normalizar_apelido(self.apelido)
        if self.email_institucional:
            self.email_institucional = self.email_institucional.strip().lower()
        # Com save(update_fields=[...]), o campo derivado precisa ir junto,
        # senão a unicidade do apelido quebra sem erro.
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "apelido" in update_fields:
            kwargs["update_fields"] = {*update_fields, "apelido_normalizado"}
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
