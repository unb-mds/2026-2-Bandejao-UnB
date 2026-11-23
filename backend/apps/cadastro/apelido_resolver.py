"""Regras do apelido no cadastro (RN02, RF01.5, ADR 0002, Cadastro N4 4a).

- Digitado (Estudante, ou Professor/Servidor que preferir digitar): formato
  da RN02 e disponibilidade; se falhar, o cadastro é rejeitado (422).
- Extraído do e-mail (Professor/Servidor): sem os caracteres não
  alfanuméricos; se ficar em uso ou fora do tamanho, o erro é recuperável
  (409) e traz uma sugestão livre para a pessoa confirmar ou trocar.
"""

import re
import unicodedata

from django.core.exceptions import ValidationError

from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.erros import ApelidoIndisponivelError, CadastroInvalidoError
from apps.cadastro.models import (
    APELIDO_TAMANHO_MAXIMO,
    APELIDO_TAMANHO_MINIMO,
    MENSAGEM_APELIDO,
    normalizar_apelido,
    validar_apelido,
)

MENSAGEM_APELIDO_EM_USO = "Este apelido já está em uso. Escolha outro."
PEDIDO_DE_APELIDO = "Escolha um apelido para exibir nas suas avaliações."
# A raiz da sugestão é cortada aqui para sobrar espaço para o número (como no
# simulado do front, #119). Com 3 dígitos ou mais, a raiz encurta mais.
TAMANHO_RAIZ_SUGESTAO = 18
TENTATIVAS_SUGESTAO = 999


class ApelidoResolver:
    def __init__(self, conta_repository: ContaRepository | None = None):
        self.conta_repository = conta_repository or ContaRepository()

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
        try:
            validar_apelido(apelido)
        except ValidationError:
            raise self.indisponivel(apelido) from None
        if not self.validar_disponibilidade(apelido):
            raise self.indisponivel(apelido)
        return apelido

    def validar_disponibilidade(self, apelido: str) -> bool:
        """Livre sem distinguir maiúsculas nem acentos (mesma regra do UNIQUE)."""
        return not self.conta_repository.existe_apelido(apelido)

    def indisponivel(self, apelido_extraido: str) -> ApelidoIndisponivelError:
        """O 409 do apelido extraído, com uma sugestão livre."""
        if apelido_extraido:
            exibido = apelido_extraido[:APELIDO_TAMANHO_MAXIMO]
            if len(apelido_extraido) > APELIDO_TAMANHO_MAXIMO:
                exibido += "…"
            mensagem = (
                f'Não foi possível usar "{exibido}" como apelido. {PEDIDO_DE_APELIDO}'
            )
        else:
            mensagem = (
                "Não foi possível gerar um apelido a partir do seu e-mail. "
                f"{PEDIDO_DE_APELIDO}"
            )
        return ApelidoIndisponivelError(
            mensagem, apelido_sugerido=self._sugerir(apelido_extraido)
        )

    def _limpar_caracteres_nao_alfanumericos(self, texto: str) -> str:
        # Só ASCII: o apelido extraído tem que passar no formato da RN02 sem
        # depender de como cada acento é normalizado.
        return re.sub(r"[^A-Za-z0-9]", "", texto)

    def _sugerir(self, apelido: str) -> str:
        """Primeiro `<raiz><n>` livre, com no máximo 20 caracteres.

        Completa com "0" até 3 caracteres (como o simulado do front, #119) e
        busca de uma vez os apelidos em uso que começam com a raiz.
        """
        raiz = apelido.ljust(APELIDO_TAMANHO_MINIMO, "0")
        tamanho_minimo_raiz = APELIDO_TAMANHO_MAXIMO - len(str(TENTATIVAS_SUGESTAO))
        em_uso = self.conta_repository.apelidos_com_prefixo(raiz[:tamanho_minimo_raiz])
        for n in range(1, TENTATIVAS_SUGESTAO + 1):
            sufixo = str(n)
            corte = min(TAMANHO_RAIZ_SUGESTAO, APELIDO_TAMANHO_MAXIMO - len(sufixo))
            candidato = raiz[:corte] + sufixo
            if normalizar_apelido(candidato) not in em_uso:
                return candidato
        # Só com 999 apelidos iguais em uso: é um erro do sistema, não da pessoa.
        raise RuntimeError(f"Sem sugestão livre de apelido para a raiz {raiz!r}")
