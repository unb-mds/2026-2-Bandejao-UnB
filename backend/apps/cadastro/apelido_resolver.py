"""Regras do apelido no cadastro (RN02, RF01.5, ADR 0002, Cadastro N4 4a).

- Digitado (Estudante, ou Professor/Servidor depois do 409): formato da RN02
  e disponibilidade; se falhar, o cadastro é rejeitado (422).
- Extraído do e-mail (Professor/Servidor): sem os caracteres não
  alfanuméricos; se ficar em uso ou fora do tamanho, o erro é recuperável
  (409) e traz uma sugestão livre para a pessoa confirmar ou trocar.
"""

import re
import unicodedata

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.cadastro.erros import ApelidoIndisponivelError, CadastroInvalidoError
from apps.cadastro.models import MENSAGEM_APELIDO, normalizar_apelido, validar_apelido

MENSAGEM_APELIDO_EM_USO = "Este apelido já está em uso. Escolha outro."
TAMANHO_MINIMO = 3
TAMANHO_MAXIMO = 20


class ApelidoResolver:
    def resolver_manual(self, apelido_digitado: str) -> str:
        """Devolve o apelido digitado, já sem espaços nas pontas e em NFC."""
        apelido = unicodedata.normalize("NFC", apelido_digitado.strip())
        try:
            validar_apelido(apelido)
        except ValidationError as exc:
            raise CadastroInvalidoError(MENSAGEM_APELIDO) from exc
        if not self.validar_disponibilidade(apelido):
            raise CadastroInvalidoError(MENSAGEM_APELIDO_EM_USO)
        return apelido

    def resolver_extraido(self, texto_antes_do_arroba: str) -> str:
        """`maria.silva` vira `mariasilva` (RF01.4)."""
        apelido = self._limpar_caracteres_nao_alfanumericos(texto_antes_do_arroba)
        tamanho_ok = TAMANHO_MINIMO <= len(apelido) <= TAMANHO_MAXIMO
        if tamanho_ok and self.validar_disponibilidade(apelido):
            return apelido
        raise ApelidoIndisponivelError(
            f'Não foi possível usar "{apelido}" como apelido. '
            "Escolha um apelido para exibir nas suas avaliações.",
            apelido_sugerido=self._sugerir(apelido),
        )

    def validar_disponibilidade(self, apelido: str) -> bool:
        """Livre sem distinguir maiúsculas nem acentos (mesma regra do UNIQUE)."""
        return not (
            get_user_model()
            .objects.filter(apelido_normalizado=normalizar_apelido(apelido))
            .exists()
        )

    def _limpar_caracteres_nao_alfanumericos(self, texto: str) -> str:
        # Só ASCII: o apelido extraído tem que passar no formato da RN02 sem
        # depender de como cada acento é normalizado.
        return re.sub(r"[^A-Za-z0-9]", "", texto)

    def _sugerir(self, apelido: str) -> str:
        """Primeiro `<raiz><n>` livre, com no máximo 20 caracteres.

        Mesma regra do simulado do front (#119): completa com "0" até 3
        caracteres e corta a raiz em 18, para caber o número.
        """
        raiz = apelido.ljust(TAMANHO_MINIMO, "0")
        n = 1
        while True:
            sufixo = str(n)
            candidato = raiz[: min(18, TAMANHO_MAXIMO - len(sufixo))] + sufixo
            if self.validar_disponibilidade(candidato):
                return candidato
            n += 1
