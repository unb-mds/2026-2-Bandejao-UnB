"""Configuração dos parâmetros do Anexo A (BD-04, #90).

As classes de configuração compartilhadas ficam neste módulo, com atributos
em snake_case. Exemplo:
`from config.parametros import AvisoPrivacidadeConfig`.

Valores usados diretamente pelo Django permanecem no settings.
ParametrosSessaoConfig().duracao_segundos e
ParametrosLeitorConfig().url_pagina consultam os settings a cada acesso.

O fuso é definido por TIME_ZONE no settings.
Configurações que consultam CAMPUS permanecem nos respectivos apps.
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

    @property
    def duracao_segundos(self) -> int:
        return settings.SESSION_COOKIE_AGE


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


class ParametrosLeitorConfig:
    """Parâmetros da fonte e da verificação do cardápio, conforme o Anexo A."""

    intervalo_verificacao: Final = timedelta(hours=3)
    # Convenção de date.weekday(): segunda-feira = 0.
    dia_alerta_nao_publicado: Final = 0
    horario_alerta_nao_publicado: Final = time(12, 0)

    @property
    def url_pagina(self) -> str:
        return settings.URL_PAGINA_CARDAPIO


class ParametrosBackupConfig:
    """Periodicidade e retenção dos backups definidas no Anexo A."""

    retencao: Final = timedelta(days=7)
    intervalo: Final = timedelta(days=1)


class ParametrosLocalizacaoConfig:
    """Parâmetros de localização; valores pendentes exigem definição da equipe."""

    tempo_nova_deteccao: Final = timedelta(minutes=30)
    tempo_limite_leitura: Final = timedelta(seconds=5)

    # None representa parâmetro ainda não definido, nunca validação dispensada.
    precisao_minima_metros: Final[float | None] = None
    idade_maxima_posicao: Final[timedelta | None] = None


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
