"""Limites de taxa por IP e por conta (#123).

Duas catracas, como na entrada do RU:

- `LimitePorIP` (e as subclasses, uma por rota): conta os pedidos de cada IP
  numa janela. Passou do limite, o DRF levanta `Throttled`, que o tratador de
  `config/excecoes.py` transforma em 429 `limite_excedido` com `Retry-After`.
- `LimiteReenvioPorConta`: conta quantos links uma conta recebeu. É
  silencioso: quem chama não manda o e-mail, mas responde 200 do mesmo jeito,
  para não revelar quais contas existem (RF02.2).

Os números ficam no `LimiteDeTaxaConfig` (`config/parametros.py`), e os
contadores, no cache em banco (`CACHES` do settings.py), que vale para todos
os workers do Gunicorn.
"""

import logging

from django.core.cache import cache
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.throttling import SimpleRateThrottle

from config.parametros import LimiteDeTaxaConfig

logger = logging.getLogger(__name__)


def ler_limite(valor: str) -> tuple[int, int]:
    """`"3/hour"` -> `(3, 3600)`: quantos pedidos cabem em quantos segundos.

    Usa o mesmo leitor do DRF (o `self` dele não é usado), para o limite por
    conta e o por IP entenderem o texto do mesmo jeito.
    """
    return SimpleRateThrottle.parse_rate(None, valor)


class LimitePorIP(SimpleRateThrottle):
    """Conta os pedidos de um IP numa rota. O `scope` é o atributo do LimiteDeTaxaConfig.

    O IP vem do `get_ident` do DRF, que segue o `NUM_PROXIES` do settings.py:
    atrás do Caddy, é o último endereço do `X-Forwarded-For` (o que o Caddy
    acrescentou); sem proxy, o `REMOTE_ADDR`. Vale também para quem já tem
    sessão (por isso não é o `AnonRateThrottle`, que ignora quem está logado).
    """

    cache_format = "limite_%(scope)s_%(ident)s"

    def get_rate(self):
        # Lido a cada pedido, e não do DEFAULT_THROTTLE_RATES (que o DRF lê uma
        # vez só, ao importar): os testes trocam o número com monkeypatch.
        return getattr(LimiteDeTaxaConfig, self.scope)

    def get_cache_key(self, request, view):
        # O IP não fica em claro na tabela do cache: o HMAC (com a SECRET_KEY)
        # dá sempre a mesma chave para o mesmo IP, mas não deixa voltar dela
        # para o IP.
        ident = salted_hmac(
            "limite_de_taxa", self.get_ident(request), algorithm="sha256"
        ).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}

    def timer(self):
        # Mesmo relógio dos testes (mock em django.utils.timezone.now) e do
        # cache em banco, que também usa o timezone.now para vencer as linhas.
        return timezone.now().timestamp()


class LimiteCadastroPorIP(LimitePorIP):
    """POST /api/cadastro/ (RF01)."""

    scope = "cadastro_por_ip"


class LimiteReenvioPorIP(LimitePorIP):
    """POST /api/reenviar-confirmacao/ (RF02.2)."""

    scope = "reenvio_por_ip"


class LimiteLoginPorIP(LimitePorIP):
    """POST /api/sessao/ (RF03). O GET e o DELETE da mesma rota ficam sem limite."""

    scope = "login_por_ip"


class LimiteReenvioPorConta:
    """Quantos links uma conta recebeu na janela. Silencioso: quem chama responde 200.

    Guarda no cache a lista dos horários dos envios (janela deslizante, como o
    DRF faz por IP). Não usa `cache.incr`: ele regrava a chave com o tempo
    padrão do cache (300 s), e a janela de 1 hora viraria 5 minutos.
    """

    def permite(self, conta) -> bool:
        """True e registra o envio; False (com aviso no log) se a conta passou do limite."""
        maximo, janela = ler_limite(LimiteDeTaxaConfig.reenvio_por_conta)
        chave = f"limite_reenvio_por_conta_{conta.pk}"
        agora = timezone.now().timestamp()
        historico = [t for t in cache.get(chave, []) if t > agora - janela]
        if len(historico) >= maximo:
            # Só o id da conta: a matrícula/SIAPE e o e-mail não vão para o
            # log (RI10).
            logger.warning("Reenvio ignorado: limite da conta %s", conta.pk)
            return False
        cache.set(chave, [agora, *historico], janela)
        return True
