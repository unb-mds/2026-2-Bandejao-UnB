"""TentativaLoginTracker: bloqueio do login por tentativas (RF03.2, Cadastro N4 4c).

O contador e o início da janela ficam na própria conta. Os limites e a
duração do bloqueio vêm de ParametrosCadastroConfig (Anexo A).

Quem chama (o LoginService) trava a linha da conta (select_for_update)
antes, para duas tentativas simultâneas não contarem como uma só.
"""

import logging
import math

from django.utils import timezone

from apps.cadastro.models import Usuario
from config.parametros import ParametrosCadastroConfig

logger = logging.getLogger(__name__)


class TentativaLoginTracker:
    CAMPOS = ("tentativas_login_falhas", "primeira_falha_login_em", "bloqueado_ate")

    def esta_bloqueado(self, conta: Usuario) -> bool:
        return self.segundos_restantes(conta) > 0

    def segundos_restantes(self, conta: Usuario) -> int:
        """Quanto falta para o bloqueio acabar, arredondado para cima (0 se não há)."""
        if conta.bloqueado_ate is None:
            return 0
        restante = (conta.bloqueado_ate - timezone.now()).total_seconds()
        return max(0, math.ceil(restante))

    def registrar_tentativa(self, conta: Usuario, sucesso: bool) -> None:
        """Conta a falha e aplica o bloqueio configurado, ou zera tudo no acerto.

        Grava só os campos do bloqueio: o resto da conta em memória pode estar
        velho.
        """
        if sucesso:
            if conta.tentativas_login_falhas == 0 and conta.bloqueado_ate is None:
                return
            conta.tentativas_login_falhas = 0
            conta.primeira_falha_login_em = None
            conta.bloqueado_ate = None
        else:
            self._contar_falha(conta, timezone.now())
        conta.save(update_fields=self.CAMPOS)

    def _contar_falha(self, conta: Usuario, agora) -> None:
        inicio = conta.primeira_falha_login_em
        if inicio is None or agora >= inicio + ParametrosCadastroConfig.login_janela:
            # Janela nova: o bloqueio antigo, se houver, já passou.
            conta.tentativas_login_falhas = 1
            conta.primeira_falha_login_em = agora
            conta.bloqueado_ate = None
        else:
            conta.tentativas_login_falhas += 1

        if (
            conta.tentativas_login_falhas
            >= ParametrosCadastroConfig.login_max_tentativas
        ):
            conta.bloqueado_ate = agora + ParametrosCadastroConfig.login_bloqueio
            # Só o id da conta: a matrícula/SIAPE não vai para o log (RI10).
            logger.warning(
                "Login bloqueado por %s min para a conta %s",
                int(ParametrosCadastroConfig.login_bloqueio.total_seconds() // 60),
                conta.pk,
            )
