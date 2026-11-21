"""AlertaEquipeService: avisa a equipe quando a leitura falha (Leitor N4 4b, ADR 0006).

Analogia: é o alarme de incêndio com soneca. Todo alarme fica anotado no
livro (ALERTA_LEITURA_CARDAPIO), mas a sirene (o e-mail) toca no máximo 3
vezes por dia e com 6 horas entre um toque e outro, por campus e tipo de
falha. Assim uma falha que dura dias avisa todo dia, sem virar ruído a
cada 3 horas do cron.

O e-mail vai para `settings.EMAIL_EQUIPE` (ADR 0012), pelo mesmo Serviço de
E-mail do cadastro. Uma falha no envio não derruba a leitura (ADR 0006): o
alerta continua gravado, e o envio que falhou não conta no limite.
"""

import logging
import smtplib
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.cardapio.models import (
    AlertaLeituraCardapio,
    Campus,
    ContadorAlerta,
    Refeicao,
    TipoAlerta,
)

logger = logging.getLogger(__name__)

ASSUNTO = "[Bandejão UnB] {tipo}: {campus}"
CORPO = """O Leitor de Cardápio registrou um alerta.

Campus: {campus}
Tipo: {tipo}
Quando: {quando}

{detalhe}

O cardápio válido anterior foi mantido (RF06.4), ou a refeição foi publicada
só em texto, sem marcadores (RF06.3). O alerta está na tabela
alerta_leitura_cardapio (id {id}); marque-o como resolvido depois de tratar.

No máximo {maximo} e-mails por dia para o mesmo campus e tipo de falha.
"""


class AlertaEquipeService:
    MAX_AVISOS_POR_DIA = 3
    INTERVALO_MINIMO = timedelta(hours=6)

    def registrar_alerta(
        self,
        tipo: TipoAlerta,
        campus: Campus,
        detalhe: str,
        refeicao: Refeicao | None = None,
        *,
        agora: datetime,
    ) -> AlertaLeituraCardapio:
        """Grava o alerta e, se o limite deixar, envia o e-mail à equipe.

        `detalhe` diz a etapa que falhou, a semana e a URL; nunca dado de
        usuário. `refeicao` é nula quando o alerta é do PDF inteiro.
        """
        alerta = AlertaLeituraCardapio.objects.create(
            campus=campus, refeicao=refeicao, tipo=tipo, mensagem=detalhe
        )
        if self._deve_enviar(tipo, campus, agora) and self._enviar(alerta, agora):
            contador, _ = ContadorAlerta.objects.get_or_create(
                campus=campus, tipo=tipo, data=timezone.localdate(agora)
            )
            contador.quantidade_enviada += 1
            contador.ultimo_envio_em = agora
            contador.save(update_fields=["quantidade_enviada", "ultimo_envio_em"])
        return alerta

    def zerar_contador(self, campus: Campus, *, agora: datetime) -> None:
        """A leitura do campus voltou a funcionar: a contagem do dia recomeça.

        Só o dia corrente (de Brasília); os dias anteriores ficam como
        histórico e não pesam no limite, que é diário.
        """
        ContadorAlerta.objects.filter(
            campus=campus, data=timezone.localdate(agora)
        ).delete()

    def _deve_enviar(self, tipo: TipoAlerta, campus: Campus, agora: datetime) -> bool:
        """Menos de 3 envios no dia e pelo menos 6 h desde o último envio do
        mesmo campus e tipo, inclusive o da véspera (a virada do dia não
        encurta o intervalo)."""
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

    def _enviar(self, alerta: AlertaLeituraCardapio, agora: datetime) -> bool:
        """Envia o e-mail. Devolve False, sem levantar, se o envio falhou."""
        tipo = TipoAlerta(alerta.tipo).label
        try:
            send_mail(
                ASSUNTO.format(tipo=tipo, campus=alerta.campus.nome),
                CORPO.format(
                    campus=alerta.campus.nome,
                    tipo=tipo,
                    quando=timezone.localtime(agora).strftime("%d/%m/%Y %H:%M"),
                    detalhe=alerta.mensagem,
                    id=alerta.pk,
                    maximo=self.MAX_AVISOS_POR_DIA,
                ),
                # None: usa o DEFAULT_FROM_EMAIL (nao-responda@..., ADR 0012).
                None,
                [settings.EMAIL_EQUIPE],
            )
        except (smtplib.SMTPException, OSError) as exc:
            # SMTP ou rede (conexão recusada, timeout, TLS), como no cadastro:
            # a leitura segue e o fallback do RF06 já foi aplicado (ADR 0006).
            # Só o nome da exceção vai para o log, sem o endereço.
            logger.error(
                "Falha ao enviar o e-mail do alerta %s (campus %s): %s",
                alerta.pk,
                alerta.campus_id,
                type(exc).__name__,
            )
            return False
        return True
