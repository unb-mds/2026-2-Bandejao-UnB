"""Validadores de formato do cadastro (RN01, RF01.1 a RF01.4, Cadastro N4 4a).

Cada método só responde se o valor passa na regra. A mensagem mostrada ao
usuário fica com o `CadastroService`, que sabe qual regra falhou.
O sistema confere apenas o formato, não a existência (L01).
"""

import re
from datetime import date
from itertools import pairwise

from django.utils import timezone

from config.parametros import ParametrosCadastroConfig

# [0-9] em vez de \d: \d aceitaria dígitos de outros alfabetos ("２", "٣").
# `fullmatch` evita o `$`, que aceitaria uma quebra de linha no fim.
FORMATO_MATRICULA = re.compile(r"[0-9]{9}")
FORMATO_SIAPE = re.compile(r"[0-9]{7}")
EMAIL_ESTUDANTE = re.compile(r"[^@\s]+@aluno\.unb\.br", re.IGNORECASE)
EMAIL_PROFESSOR_SERVIDOR = re.compile(r"[^@\s]+@unb\.br", re.IGNORECASE)

TAMANHO_MINIMO_SENHA = 8


class MatriculaValidator:
    """Matrícula de Estudante: três checagens independentes (RN01, RF01.3)."""

    def __init__(self, hoje: date | None = None):
        # O ano máximo é recalculado pela data: o ano novo é aceito sem mudar
        # código. `hoje` existe para os testes.
        self.hoje = hoje

    def validar_formato(self, matricula: str) -> bool:
        """Exatamente 9 dígitos. Matrícula de 8 dígitos (antes de 2010) não passa (L10)."""
        return bool(FORMATO_MATRICULA.fullmatch(matricula))

    def validar_prefixo_ano_semestre(self, matricula: str) -> bool:
        """Os 2 primeiros dígitos são um ano de 2010 até o ano corrente.

        O nome é o do Nível 4, mas só o ano é conferido: o 3º dígito (semestre)
        é 1 ou 2 na graduação, sem confirmação para os outros níveis de ensino
        (ADR 0002, L16). O dia vem de `timezone.localdate()`, então a virada de
        ano segue o `TIME_ZONE` do projeto.
        """
        ano = matricula[:2]
        if not re.fullmatch(r"[0-9]{2}", ano):
            return False
        hoje = self.hoje or timezone.localdate()
        return (
            ParametrosCadastroConfig.primeiro_ano_matricula
            <= int(ano)
            <= hoje.year % 100
        )

    def validar_sequencia_digitos(self, matricula: str) -> bool:
        """Rejeita os 6 dígitos finais todos iguais ou em sequência de passo 1.

        Passo 1 para cima (`123456`) ou para baixo (`654321`). `251567890`
        passa, porque de 9 para 0 o passo não é 1.
        """
        final = matricula[3:]
        if not re.fullmatch(r"[0-9]{6}", final):
            return False
        digitos = [int(c) for c in final]
        passos = {b - a for a, b in pairwise(digitos)}
        return passos not in ({0}, {1}, {-1})


class SiapeValidator:
    def validar_formato(self, siape: str) -> bool:
        """SIAPE/matrícula funcional com exatamente 7 dígitos (RN01, RF01.4)."""
        return bool(FORMATO_SIAPE.fullmatch(siape))


class EmailInstitucionalValidator:
    """Domínio do e-mail institucional de cada tipo de usuário (ADR 0002)."""

    def validar_formato_estudante(self, email: str) -> bool:
        """`algo@aluno.unb.br`. A parte antes do "@" é validada como matrícula."""
        return bool(EMAIL_ESTUDANTE.fullmatch(email))

    def validar_formato_professor_servidor(self, email: str) -> bool:
        """`qualquer-texto@unb.br` (ADR 0002)."""
        return bool(EMAIL_PROFESSOR_SERVIDOR.fullmatch(email))


class SenhaValidator:
    def validar(self, senha: str) -> bool:
        """No mínimo 8 caracteres (RF01.1).

        O hash fica com o Django (`set_password`, PBKDF2), que faz o papel do
        `PasswordHasher` do Nível 4.
        """
        return len(senha) >= TAMANHO_MINIMO_SENHA
