"""Dados do cadastro que chegam ao domínio (Cadastro N4 4a).

O `CadastroEntradaSerializer` converte o corpo da API (camelCase) para esta
classe. O tipo de usuário fica fora, porque o `CadastroService.registrar`
o recebe à parte, como no Nível 4.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DadosCadastro:
    email_institucional: str
    senha: str
    # Só o booleano `True` vale como ciência do aviso (RNF07.1).
    aceite_privacidade: bool
    # Vazio quando não veio. Estudante sempre digita; professor/servidor só
    # digita se quiser trocar o apelido tirado do e-mail (ou depois do 409).
    apelido: str = ""
    # SIAPE digitado pelo professor/servidor. Ignorado para estudante.
    matricula_siape: str = ""
