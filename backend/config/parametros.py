"""Classes de configuração dos valores do Anexo A (BD-04, #90).

Os nomes das classes são os dos Níveis 4; os atributos ficam em snake_case
(`versao_atual` para `versaoAtual`). Uso:
`from config.parametros import AvisoPrivacidadeConfig`.

A BE-05 cria o arquivo só com o `AvisoPrivacidadeConfig`. A BD-04 acrescenta
as outras classes aqui mesmo, sem criar outro módulo. Valores que o Django já
lê do `settings.py` (duração da sessão, fuso) continuam lá, e a classe só os
expõe, para o número do Anexo A não ficar escrito em dois lugares.
"""

from datetime import date, time, timedelta
from typing import Final

from django.conf import settings


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


class ParametrosGamificacaoConfig:
    """Parâmetros de pontuação, sequência, patentes e ranking do Anexo A."""

    pontos_checkin: Final = 10
    pontos_resposta_saida: Final = 15
    pontos_avaliacao: Final = 5
    min_dias_semana: Final = 3
    bonus_semana: Final = 20
    limiares_patente: Final = (0, 150, 450, 900, 1500)
    tamanho_ranking: Final = 10

    # Preencher com datas confirmadas pela equipe no calendário acadêmico.
    # Sem data configurada, o período do ranking permanece aberto (RN12).
    datas_termino_semestre: Final[dict[str, date]] = {}


class ParametrosSessaoConfig:
    """Duração da sessão definida no settings, conforme a ADR 0007."""

    duracao_segundos: Final = settings.SESSION_COOKIE_AGE


class ParametrosCadastroConfig:
    """Parâmetros do Anexo A para matrícula, confirmação de e-mail e login."""

    primeiro_ano_matricula: Final = 10
    validade_confirmacao_email: Final = timedelta(hours=24)
    login_max_tentativas: Final = 5
    login_janela: Final = timedelta(minutes=10)
    login_bloqueio: Final = timedelta(minutes=10)
    validade_redefinicao_senha: Final = timedelta(hours=1)
    redefinicao_max_solicitacoes: Final = 3
    redefinicao_janela: Final = timedelta(hours=1)
