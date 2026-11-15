"""Classes de configuração dos valores do Anexo A (BD-04, #90).

Os nomes das classes são os dos Níveis 4; os atributos ficam em snake_case
(`versao_atual` para `versaoAtual`). Uso:
`from config.parametros import AvisoPrivacidadeConfig`.

A BE-05 cria o arquivo só com o `AvisoPrivacidadeConfig`. A BD-04 acrescenta
as outras classes aqui mesmo, sem criar outro módulo. Valores que o Django já
lê do `settings.py` (duração da sessão, fuso) continuam lá, e a classe só os
expõe, para o número do Anexo A não ficar escrito em dois lugares.
"""

from typing import Final


class AvisoPrivacidadeConfig:
    """Versão do aviso de privacidade em vigor (RF11, RNF07.1, Cadastro N4 4a e 4d).

    A versão é a data do aviso, em `AAAA-MM-DD`. Quando o texto do aviso
    mudar, troca-se a data: quem aceitou a versão anterior vê o aviso de novo.
    """

    # Igual à "Versão" de docs/requisitos/aviso-de-privacidade.md (DOC-03).
    # Um teste falha se as duas ficarem diferentes.
    versao_atual: Final = "2026-11-14"
