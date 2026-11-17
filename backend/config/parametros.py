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


class LimiteDeTaxaConfig:
    """Limites de taxa das rotas públicas que criam conta ou mandam e-mail (#123).

    Como a catraca do RU: cada IP (ou conta) tem um contador por rota, que
    zera quando a janela passa. Acima do limite, o IP recebe 429
    `limite_excedido`; o limite por conta do reenvio é silencioso (RF02.2).

    Formato do DRF: "<número>/<unidade>", com unidade second, minute, hour ou
    day. Só a primeira letra da unidade conta: "5/mes" vira 5 por MINUTO, sem
    erro; "5/10m" quebra com KeyError (500 no primeiro pedido). Um teste em
    tests/test_parametros.py confere o formato.

    Os números não são menores porque a rede Wi-Fi da UnB sai por poucos IPs
    (NAT): uma turma inteira se cadastrando conta como um IP só. Os nomes dos
    atributos são os `scope` das classes de `apps/cadastro/limite_de_taxa.py`.
    """

    # Segura a criação em massa de contas pendentes com matrícula alheia.
    cadastro_por_ip: Final = "40/hour"
    # Segura o disparo de e-mail em massa e protege a cota diária do Brevo.
    reenvio_por_ip: Final = "10/hour"
    # Mesmo número da redefinição de senha no Anexo A: protege a caixa de
    # e-mail da vítima mesmo com IPs diferentes.
    reenvio_por_conta: Final = "3/hour"
    # Segura o password spraying (uma senha em muitas contas).
    login_por_ip: Final = "60/hour"
