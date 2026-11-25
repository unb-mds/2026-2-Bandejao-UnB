"""AlertaEquipeService: avisa a equipe quando a leitura falha (Leitor N4 4b, ADR 0006).

Analogia: é o livro de ocorrências com um carteiro de horário marcado. Todo
problema é anotado no livro na hora (ALERTA_LEITURA_CARDAPIO). No fim da
execução do campus, o carteiro leva à equipe um envelope só, com tudo o que
ainda não foi entregue. Ele sai no máximo 3 vezes por dia e com 6 horas
entre uma saída e outra, por campus e tipo de falha (ADR 0006); numa falha
que vai e volta, o `zerar_contador` recomeça a contagem do dia, e o limite
passa a ser o das 6 horas: até 4 e-mails no dia. O que fica para trás vai no
envelope seguinte: nenhuma anotação fica sem e-mail para sempre, nem o "não
publicado", que é avaliado por último (revisão do PR #218).

O e-mail vai para `settings.EMAIL_EQUIPE` (ADR 0006 e 0012), pelo mesmo
Serviço de E-mail do cadastro. Uma falha no envio não derruba a leitura
(ADR 0006): os alertas continuam gravados, sem `email_enviado_em`, e o envio
que falhou não conta no limite.
"""

import logging
import smtplib
from datetime import datetime, timedelta
from typing import NamedTuple

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    ContadorAlerta,
    Refeicao,
    TipoAlerta,
)

logger = logging.getLogger(__name__)

# Quantos alertas o e-mail lista; os outros aparecem só na contagem (todos
# continuam na tabela, e todos são marcados como enviados).
MAX_ALERTAS_NO_EMAIL = 20

ASSUNTO = "[Bandejão UnB] Leitor de Cardápio: {quantos} em {campus}"
CORPO = """O Leitor de Cardápio registrou {quantos} no campus {campus}.

{lista}
Cada mensagem diz a etapa que falhou e a situação do cardápio: o válido
anterior mantido (RF06.4), a refeição publicada só em texto, sem marcadores
(RF06.3), ou a semana ainda não publicada.

Os alertas estão na tabela alerta_leitura_cardapio; marque-os como resolvidos
depois de tratar. No máximo {maximo} e-mails por dia para o mesmo campus e
tipo de falha, com {intervalo} horas entre dois e-mails.
"""
ITEM = "- [{quando}] {tipo} (alerta {id}): {mensagem}\n"


class ResultadoEnvio(NamedTuple):
    """`enviados`: quantos alertas foram no e-mail. `falhou`: havia o que
    enviar, mas o e-mail não saiu (os alertas continuam pendentes)."""

    enviados: int
    falhou: bool


def _quantos(n):
    return f"{n} alerta" if n == 1 else f"{n} alertas"


class AlertaEquipeService:
    MAX_AVISOS_POR_DIA = 3
    INTERVALO_MINIMO = timedelta(hours=6)

    def registrar_alerta(
        self,
        tipo: TipoAlerta,
        campus: Campus,
        detalhe: str,
        refeicao: Refeicao | None = None,
    ) -> AlertaLeituraCardapio:
        """Grava o alerta, sem enviar e-mail (quem envia é `enviar_pendentes`).

        Só escreve no banco: pode ficar dentro da transação da semana, junto
        com o cardápio. `detalhe` diz a etapa que falhou, a semana e a URL;
        nunca dado de usuário. `refeicao` é nula quando o alerta é do PDF
        inteiro.
        """
        return AlertaLeituraCardapio.objects.create(
            campus=campus, refeicao=refeicao, tipo=tipo, mensagem=detalhe
        )

    def enviar_pendentes(self, campus: Campus, *, agora: datetime) -> ResultadoEnvio:
        """Um e-mail com os alertas do campus ainda sem e-mail, dos tipos que
        o limite deixa enviar agora. "Nada pendente" e "limite" devolvem
        `(0, False)`; o envio que falhou devolve `(0, True)`, para o comando
        sair com erro e o cron ver (segunda revisão do PR #218).
        """
        pendentes = AlertaLeituraCardapio.objects.filter(
            campus=campus, resolvido=False, email_enviado_em__isnull=True
        )
        tipos = [
            tipo
            for tipo in pendentes.values_list("tipo", flat=True).distinct()
            if self._deve_enviar(tipo, campus, agora)
        ]
        # Os mais antigos primeiro: numa sequência longa de falhas, a causa
        # original fica na lista do e-mail.
        alertas = list(pendentes.filter(tipo__in=tipos).order_by("id"))
        if not alertas:
            return ResultadoEnvio(0, False)
        if not self._enviar(campus, alertas, agora):
            return ResultadoEnvio(0, True)
        with transaction.atomic():
            AlertaLeituraCardapio.objects.filter(pk__in=[a.pk for a in alertas]).update(
                email_enviado_em=agora
            )
            for tipo in tipos:
                self._contar_envio(campus, tipo, agora)
        return ResultadoEnvio(len(alertas), False)

    def zerar_contador(self, campus: Campus, *, agora: datetime) -> None:
        """A leitura do campus voltou a funcionar: a contagem do dia recomeça.

        Zera só a quantidade do dia corrente (de Brasília) e mantém o
        `ultimo_envio_em`: o intervalo de 6 h continua valendo numa falha
        intermitente (revisão do PR #218, item 5). Por isso, numa falha que
        vai e volta, o campus pode receber até 4 e-mails num dia (de 6 em 6
        horas), e não mais que isso.
        """
        ContadorAlerta.objects.filter(
            campus=campus, data=timezone.localdate(agora)
        ).update(quantidade_enviada=0)

    def _deve_enviar(self, tipo: TipoAlerta, campus: Campus, agora: datetime) -> bool:
        """Menos de 3 envios no dia (de Brasília) e pelo menos 6 h desde o
        último envio do mesmo campus e tipo, inclusive o da véspera e mesmo
        depois de `zerar_contador`."""
        enviados = ContadorAlerta.objects.filter(campus=campus, tipo=tipo)
        hoje = enviados.filter(data=timezone.localdate(agora)).first()
        if hoje is not None and hoje.quantidade_enviada >= self.MAX_AVISOS_POR_DIA:
            return False
        ultimo = (
            enviados.filter(ultimo_envio_em__isnull=False)
            .order_by("-ultimo_envio_em")
            .values_list("ultimo_envio_em", flat=True)
            .first()
        )
        return ultimo is None or agora - ultimo >= self.INTERVALO_MINIMO

    @staticmethod
    def _contar_envio(campus: Campus, tipo: TipoAlerta, agora: datetime) -> None:
        # F(): o incremento é feito pelo banco, sem ler e regravar o valor.
        contador, _ = ContadorAlerta.objects.get_or_create(
            campus=campus, tipo=tipo, data=timezone.localdate(agora)
        )
        ContadorAlerta.objects.filter(pk=contador.pk).update(
            quantidade_enviada=F("quantidade_enviada") + 1, ultimo_envio_em=agora
        )

    def _enviar(self, campus: Campus, alertas: list, agora: datetime) -> bool:
        """Envia o e-mail. Devolve False, sem levantar, se o envio falhou."""
        lista = "".join(
            ITEM.format(
                quando=timezone.localtime(a.ocorrido_em).strftime("%d/%m/%Y %H:%M"),
                tipo=TipoAlerta(a.tipo).label,
                id=a.pk,
                mensagem=a.mensagem,
            )
            for a in alertas[:MAX_ALERTAS_NO_EMAIL]
        )
        if len(alertas) > MAX_ALERTAS_NO_EMAIL:
            lista += f"- e mais {_quantos(len(alertas) - MAX_ALERTAS_NO_EMAIL)}.\n"
        quantos = _quantos(len(alertas))
        try:
            enviados = send_mail(
                ASSUNTO.format(quantos=quantos, campus=campus.nome),
                f"Enviado em {timezone.localtime(agora):%d/%m/%Y %H:%M} "
                "(horário de Brasília).\n\n"
                + CORPO.format(
                    quantos=quantos,
                    campus=campus.nome,
                    lista=lista,
                    maximo=self.MAX_AVISOS_POR_DIA,
                    intervalo=int(self.INTERVALO_MINIMO.total_seconds() // 3600),
                ),
                # None: usa o DEFAULT_FROM_EMAIL (nao-responda@..., ADR 0012).
                None,
                [settings.EMAIL_EQUIPE],
            )
        except (smtplib.SMTPException, OSError) as exc:
            # SMTP ou rede (conexão recusada, timeout, TLS), como no cadastro.
            # Só o nome da exceção e o código SMTP vão para o log, sem o
            # endereço: o código separa senha errada (535) de destinatário
            # recusado (550).
            logger.error(
                "Falha ao enviar o e-mail de alertas do campus %s: %s (SMTP %s)",
                campus.pk,
                type(exc).__name__,
                getattr(exc, "smtp_code", None),
            )
            return False
        except Exception:
            # Configuração de e-mail, cabeçalho, codificação: uma falha aqui
            # não pode impedir a leitura do cardápio (ADR 0006).
            logger.exception(
                "Erro inesperado ao enviar o e-mail de alertas do campus %s",
                campus.pk,
            )
            return False
        if enviados != 1:
            # O Django descarta destinatário vazio e devolve 0, sem levantar.
            logger.error(
                "Falha ao enviar o e-mail de alertas do campus %s: nenhum e-mail "
                "enviado (confira o EMAIL_EQUIPE)",
                campus.pk,
            )
            return False
        return True
