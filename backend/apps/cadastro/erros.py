"""Erros do cadastro (Cadastro N4 4a e 4b).

As views traduzem cada um para o contrato:
- `CadastroInvalidoError` (e as duplicidades) -> 422 `dados_invalidos`;
- `ApelidoIndisponivelError` -> 409 `apelido_indisponivel` com `apelidoSugerido`;
- `TokenExpiradoOuInvalidoError` -> 410 `token_invalido_ou_expirado`.
"""

# RF01.5 com a decisão do contrato: matrícula/SIAPE e e-mail repetidos dão a
# mesma mensagem, sem dizer qual dos dois já existe.
MENSAGEM_JA_CADASTRADO = "Matrícula/SIAPE ou e-mail já cadastrados."


class CadastroInvalidoError(Exception):
    """Dado rejeitado. `mensagem` é o texto que o front mostra."""

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class IdentificadorJaCadastradoError(CadastroInvalidoError):
    def __init__(self):
        super().__init__(MENSAGEM_JA_CADASTRADO)


class EmailJaCadastradoError(CadastroInvalidoError):
    def __init__(self):
        super().__init__(MENSAGEM_JA_CADASTRADO)


class ApelidoIndisponivelError(Exception):
    """O apelido extraído do e-mail não pôde ser usado (RN02, ADR 0002).

    É recuperável: a pessoa reenvia o cadastro com um apelido digitado. Por
    isso não herda de `CadastroInvalidoError`.
    """

    def __init__(self, mensagem: str, apelido_sugerido: str):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.apelido_sugerido = apelido_sugerido


class TokenExpiradoOuInvalidoError(Exception):
    """Link de confirmação inexistente, expirado ou já usado (RF02.1).

    Os três casos dão o mesmo erro de propósito: quem tenta adivinhar um token
    não descobre se acertou um que já venceu.
    """
