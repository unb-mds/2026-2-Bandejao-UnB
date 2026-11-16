"""Classes de configuração dos valores do Anexo A (BD-04, #90).

Os nomes das classes são os dos Níveis 4; os atributos ficam em snake_case
(`versao_atual` para `versaoAtual`). Uso:
`from config.parametros import AvisoPrivacidadeConfig`.

A BE-05 cria o arquivo só com o `AvisoPrivacidadeConfig`. A BD-04 acrescenta
as outras classes aqui mesmo, sem criar outro módulo. Valores que o Django já
lê do `settings.py` (duração da sessão, fuso) continuam lá, e a classe só os
expõe, para o número do Anexo A não ficar escrito em dois lugares.
"""

from datetime import time
from typing import Final


class AvisoPrivacidadeConfig:
    """Versão do aviso de privacidade em vigor (RF11, RNF07.1, Cadastro N4 4a e 4d).

    A versão é a data do aviso, em `AAAA-MM-DD`. Quando o texto do aviso
    mudar, troca-se a data: quem aceitou a versão anterior vê o aviso de novo.
    """

    # Igual à "Versão" de docs/requisitos/aviso-de-privacidade.md (DOC-03).
    # Um teste falha se as duas ficarem diferentes.
    versao_atual: Final = "2026-11-14"


class HorariosRefeicaoConfig:
    """Intervalos do Anexo A; dias e refeições servidos vêm do PDF."""

    horario_cafe: Final = (time(7, 0), time(9, 30))
    horario_almoco: Final = (time(11, 0), time(14, 30))
    horario_jantar: Final = (time(17, 0), time(19, 30))


class ParametrosFilaConfig:
    """Parâmetros do Anexo A usados pela fila e sua retenção."""

    primeira_pergunta_min: Final = 15
    repeticao_min: Final = 10
    expiracao_min: Final = 60
    ponto_medio_ate5_min: Final = 2.5
    ponto_medio5a10_min: Final = 7.5

    faixa_minutos: Final = 15
    janela_semanas: Final = 4
    min_dias_distintos: Final = 3
    cortes: Final = (25, 50, 75)
    min_tempos_espera: Final = 3
    min_dias_espera: Final = 2
    retencao_semanas: Final = 4
