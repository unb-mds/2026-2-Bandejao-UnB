"""Formatos de entrada e saída do app cadastro (contrato OpenAPI, BE-03)."""

from rest_framework import serializers

from apps.cadastro.models import TipoUsuario
from config.erros import ErroSerializer


class CadastroEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/cadastro/ (RF01, Cadastro N4 4a)."""

    tipoUsuario = serializers.ChoiceField(choices=TipoUsuario.choices)
    emailInstitucional = serializers.EmailField()
    senha = serializers.CharField(min_length=8, write_only=True)
    apelido = serializers.CharField(
        required=False,
        help_text=(
            "Obrigatório para estudante. Professor/servidor só envia depois "
            "de um 409 apelido_indisponivel."
        ),
    )
    matriculaSiape = serializers.CharField(
        required=False,
        help_text="SIAPE de 7 dígitos. Só para professor/servidor.",
    )
    aceitePrivacidade = serializers.BooleanField(
        help_text="Ciência do aviso de privacidade (RNF07.1). Precisa ser true.",
    )


class CadastroCriadoSerializer(serializers.Serializer):
    """Resposta 201: a conta fica pendente até confirmar o e-mail (RF02)."""

    emailInstitucional = serializers.EmailField()
    status = serializers.CharField(help_text='Sempre "pendente".')


class ApelidoIndisponivelSerializer(ErroSerializer):
    """Resposta 409: o apelido tirado do e-mail não pôde ser usado."""

    apelidoSugerido = serializers.CharField()


class ReenvioConfirmacaoEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/reenviar-confirmacao/ (RF02.2, Cadastro N4 4b).

    PROVISÓRIO: a documentação não diz como o back acha a conta. Envie
    um dos dois campos (confirmar no servidor.js do front).
    """

    matriculaSiape = serializers.CharField(
        required=False,
        help_text="Quem pede o reenvio pela tela de login (conta não confirmada).",
    )
    token = serializers.CharField(
        required=False,
        help_text="Quem pede o reenvio pela tela do link expirado.",
    )


class LoginEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/sessao/ (RF03.1, Cadastro N4 4c)."""

    matriculaSiape = serializers.CharField(
        help_text="Matrícula (9 dígitos) ou SIAPE (7 dígitos), no mesmo campo.",
    )
    senha = serializers.CharField(write_only=True)


class SessaoSerializer(serializers.Serializer):
    """Quem está logado (Cadastro N4 4c). Nunca matrícula/SIAPE nem e-mail (RI10)."""

    apelido = serializers.CharField()
    # CharField de propósito (ver nota abaixo): ChoiceField geraria aviso.
    tipo = serializers.CharField(help_text='"estudante" ou "professor_servidor".')
    avisoPrivacidadePendente = serializers.BooleanField()
