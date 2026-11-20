"""Formatos de entrada e saída do app cadastro (contrato OpenAPI, BE-03)."""

from rest_framework import serializers

from apps.cadastro.dados_cadastro import DadosCadastro
from apps.cadastro.models import TipoUsuario
from config.erros import ErroSerializer


class TextoEstritoField(serializers.CharField):
    """CharField que recusa número: `0123456` chegaria como `123456`."""

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class BooleanoEstritoField(serializers.BooleanField):
    """Só o booleano do JSON. `"true"`, `1` ou `"sim"` não valem como aceite."""

    def to_internal_value(self, data):
        if not isinstance(data, bool):
            self.fail("invalid", input=data)
        return data


class CadastroEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/cadastro/ (RF01, Cadastro N4 4a)."""

    tipoUsuario = serializers.ChoiceField(choices=TipoUsuario.choices)
    # 254: o tamanho da coluna (EmailField do model).
    emailInstitucional = serializers.EmailField(max_length=254)
    # Os espaços das pontas fazem parte da senha (o login também os mantém).
    senha = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)
    # Vazio ou null contam como "não veio": o front manda "" nos campos que
    # o tipo escolhido esconde.
    apelido = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text=(
            "Obrigatório para estudante. Professor/servidor pode deixar vazio "
            "(o apelido sai do e-mail) ou digitar um, como depois de um 409 "
            "apelido_indisponivel."
        ),
    )
    matriculaSiape = TextoEstritoField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="SIAPE de 7 dígitos, como texto. Só para professor/servidor.",
    )
    aceitePrivacidade = BooleanoEstritoField(
        help_text=(
            "Ciência do aviso de privacidade (RNF07.1). Precisa ser o booleano true."
        ),
    )

    def para_dados_cadastro(self) -> DadosCadastro:
        dados = self.validated_data
        return DadosCadastro(
            email_institucional=dados["emailInstitucional"],
            senha=dados["senha"],
            aceite_privacidade=dados["aceitePrivacidade"],
            apelido=dados.get("apelido") or "",
            matricula_siape=dados.get("matriculaSiape") or "",
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

    Envie um dos dois campos. Se vierem os dois, vale o `emailInstitucional`;
    se ele não achar conta, vale o `token`.
    """

    emailInstitucional = TextoEstritoField(
        required=False,
        max_length=254,
        help_text="Quem pede o reenvio pela tela de login (conta não confirmada).",
    )
    token = serializers.CharField(
        required=False,
        help_text=(
            "Quem pede o reenvio pela tela do link expirado. Serve o token de "
            "um link já vencido ou já usado."
        ),
    )

    def validate(self, dados):
        if not dados.get("emailInstitucional") and not dados.get("token"):
            raise serializers.ValidationError("Informe emailInstitucional ou token.")
        return dados


class LoginEntradaSerializer(serializers.Serializer):
    """Corpo do POST /api/sessao/ (RF03.1, Cadastro N4 4c)."""

    # Texto estrito, como no cadastro. O domínio é conferido no LoginService
    # (EmailInstitucionalValidator, ADR 0002). 254: o tamanho da coluna.
    emailInstitucional = TextoEstritoField(
        max_length=254,
        help_text="E-mail institucional: matricula@aluno.unb.br ou nome@unb.br.",
    )
    # Sem cortar os espaços das pontas, como no cadastro.
    senha = TextoEstritoField(write_only=True, trim_whitespace=False)


class SessaoSerializer(serializers.Serializer):
    """Quem está logado (Cadastro N4 4c). Nunca matrícula/SIAPE nem e-mail (RI10)."""

    apelido = serializers.CharField()
    # CharField de propósito: um ChoiceField repetiria as opções de
    # `tipoUsuario` com outro nome de enum, e o drf-spectacular avisa
    # ("multiple names for the same choice set"), o que derruba o --fail-on-warn.
    tipo = serializers.CharField(help_text='"estudante" ou "professor_servidor".')
    avisoPrivacidadePendente = serializers.BooleanField()
