"""Validadores de formato do cadastro (RN01, RF01.1 a RF01.4, Cadastro N4 4a).

Cada método só responde se o valor passa na regra. A mensagem mostrada ao
usuário fica com o `CadastroService`, que sabe qual regra falhou.
O sistema confere apenas o formato, não a existência (L01).
"""

import re
from datetime import date
from itertools import pairwise

from django.utils import timezone

# [0-9] em vez de \d: \d aceitaria dígitos de outros alfabetos ("２", "٣").
# `fullmatch` evita o `$`, que aceitaria uma quebra de linha no fim.
FORMATO_MATRICULA = re.compile(r"[0-9]{9}")
FORMATO_SIAPE = re.compile(r"[0-9]{7}")
EMAIL_ESTUDANTE = re.compile(r"[^@\s]+@aluno\.unb\.br", re.IGNORECASE)
EMAIL_PROFESSOR_SERVIDOR = re.compile(r"[^@\s]+@unb\.br", re.IGNORECASE)

# Primeiro código de semestre aceito: 2010, 1º semestre (Anexo A).
PRIMEIRO_PREFIXO = 101
TAMANHO_MINIMO_SENHA = 8


def codigo_semestre(dia: date) -> int:
    """Código de ano/semestre do dia (ex.: 262 no 2º semestre de 2026).

    Aproximação: usa o semestre do calendário (janeiro a junho, julho a
    dezembro), e não o calendário letivo da UnB, e o dia vem de
    `timezone.localdate()` com `TIME_ZONE = "UTC"`. Na virada, um prefixo novo
    pode ser aceito algumas horas antes ou depois.
    """
    semestre = 1 if dia.month <= 6 else 2
    return (dia.year % 100) * 10 + semestre


class MatriculaValidator:
    """Matrícula de Estudante: três checagens independentes (RN01, RF01.3)."""

    def __init__(self, hoje: date | None = None):
        # A janela de prefixos é recalculada pela data: um semestre novo é
        # aceito sem mudar código. `hoje` existe para os testes.
        self.hoje = hoje

    def validar_formato(self, matricula: str) -> bool:
        """Exatamente 9 dígitos. Matrícula de 8 dígitos (antes de 2010) não passa (L10)."""
        return bool(FORMATO_MATRICULA.fullmatch(matricula))

    def validar_prefixo_ano_semestre(self, matricula: str) -> bool:
        """3 primeiros dígitos entre 101 e o semestre corrente, 3º dígito 1 ou 2."""
        prefixo = matricula[:3]
        if not re.fullmatch(r"[0-9]{2}[12]", prefixo):
            return False
        hoje = self.hoje or timezone.localdate()
        return PRIMEIRO_PREFIXO <= int(prefixo) <= codigo_semestre(hoje)

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
