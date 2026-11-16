"""Erros do cadastro e do login (Cadastro N4 4a, 4b e 4c).

As views traduzem cada um para o contrato:
- `CadastroInvalidoError` (e as duplicidades) -> 422 `dados_invalidos`;
- `ApelidoIndisponivelError` -> 409 `apelido_indisponivel` com `apelidoSugerido`;
- `TokenExpiradoOuInvalidoError` -> 410 `token_invalido_ou_expirado`;
- `IdentificadorInvalidoError` -> 422 `dados_invalidos`;
- `CredenciaisInvalidasError` -> 401 `credenciais_invalidas`;
- `ContaNaoConfirmadaError` -> 403 `conta_nao_confirmada`;
- `LoginBloqueadoError` -> 429 `login_bloqueado`.
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


class IdentificadorInvalidoError(Exception):
    """Matrícula/SIAPE fora do formato no login (RN01): nem 9 nem 7 dígitos.

    O formato é público, então dizer que ele está errado não revela conta
    nenhuma. Por isso a mensagem é específica e não conta como tentativa.
    """

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class CredenciaisInvalidasError(Exception):
    """Senha errada, conta inexistente, suspensa ou removida (RF03.1).

    Todos os casos dão o mesmo erro de propósito: a resposta não revela se a
    matrícula/SIAPE existe.
    """


class ContaNaoConfirmadaError(Exception):
    """Senha certa, mas o e-mail ainda não foi confirmado (RF02).

    Só sai com a senha certa: quem não a sabe recebe `CredenciaisInvalidasError`
    e não descobre que a conta existe.
    """


class LoginBloqueadoError(Exception):
    """5 tentativas malsucedidas em 10 minutos (RF03.2, Anexo A)."""

    def __init__(self, segundos_restantes: int):
        super().__init__(segundos_restantes)
        self.segundos_restantes = segundos_restantes
