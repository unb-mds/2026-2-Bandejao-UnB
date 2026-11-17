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

import ipaddress
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


def gravar(cache_usado, chave, valor, segundos) -> bool:
    """Grava no cache e diz se a chave ficou lá.

    O `set` do DatabaseCache engole o DatabaseError (lock, banco fora) para
    não derrubar quem chama, e devolve None dando certo ou não: o retorno não
    diz nada. Sem conferir, uma falha na tabela do cache desligaria o limite
    em silêncio. Por isso, a leitura de volta (um SELECT a mais por pedido).
    Confere só se a chave existe, e não o valor: outro pedido no mesmo
    instante pode ter gravado a lista dele (guia 9.6), e isso não é falha.
    """
    cache_usado.set(chave, valor, segundos)
    return cache_usado.get(chave) is not None


class LimitePorIP(SimpleRateThrottle):
    """Conta os pedidos de um IP numa rota. O `scope` é o atributo do LimiteDeTaxaConfig.

    O IP vem do `get_ident` do DRF, que segue o `NUM_PROXIES` do settings.py:
    atrás do Caddy, é o último endereço do `X-Forwarded-For` (o que o Caddy
    acrescentou); sem proxy, o `REMOTE_ADDR`. Vale também para quem já tem
    sessão (por isso não é o `AnonRateThrottle`, que ignora quem está logado).
    """

    cache_format = "limite_%(scope)s_%(ident)s"

    def get_ident(self, request):
        """IP do cliente, com o IPv6 agrupado pela faixa /64.

        Um aparelho IPv6 costuma receber uma faixa /64 inteira e pode trocar o
        fim do endereço à vontade: sem agrupar, cada troca seria um contador
        novo (e uma linha nova na tabela do cache). O IPv4 dentro do IPv6
        (`::ffff:1.2.3.4`) conta como o próprio IPv4. Um valor que não é IP
        (cabeçalho estranho) fica como veio.
        """
        ident = super().get_ident(request)
        try:
            ip = ipaddress.ip_address(ident)
        except ValueError:
            return ident
        if ip.version == 6:
            if ip.ipv4_mapped:
                return str(ip.ipv4_mapped)
            return str(ipaddress.ip_network(f"{ip}/64", strict=False))
        return ident

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

    def throttle_success(self):
        # O mesmo do DRF, mas conferindo a gravação (veja `gravar`). O pedido
        # segue mesmo se ela falhar: um problema no cache não pode derrubar o
        # login. Só o scope vai para o log, não o IP.
        self.history.insert(0, self.now)
        if not gravar(self.cache, self.key, self.history, self.duration):
            logger.error("Limite de taxa: contador %s não foi gravado", self.scope)
        return True


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

    Duas etapas, como o carimbo na carteirinha só depois da refeição servida:
    `permite()` só consulta, e `registrar()` conta o envio, chamado só quando
    o e-mail sai. Assim, com o Brevo fora do ar, as tentativas que falharam
    não gastam as vagas da hora.

    Guarda no cache a lista dos horários dos envios (janela deslizante, como o
    DRF faz por IP). Não usa `cache.incr`: ele regrava a chave com o tempo
    padrão do cache (300 s), e a janela de 1 hora viraria 5 minutos.
    """

    def __init__(self):
        self.maximo, self.janela = ler_limite(LimiteDeTaxaConfig.reenvio_por_conta)

    def _chave(self, conta):
        return f"limite_reenvio_por_conta_{conta.pk}"

    def _historico(self, conta, agora):
        return [t for t in cache.get(self._chave(conta), []) if t > agora - self.janela]

    def permite(self, conta) -> bool:
        """True se a conta ainda tem vaga na janela; False (com aviso no log) se não."""
        historico = self._historico(conta, timezone.now().timestamp())
        if len(historico) >= self.maximo:
            # Só o id da conta: a matrícula/SIAPE e o e-mail não vão para o
            # log (RI10).
            logger.warning("Reenvio ignorado: limite da conta %s", conta.pk)
            return False
        return True

    def registrar(self, conta) -> None:
        """Conta um link que saiu. Chame só depois de o e-mail sair."""
        agora = timezone.now().timestamp()
        historico = [agora, *self._historico(conta, agora)]
        if not gravar(cache, self._chave(conta), historico, self.janela):
            logger.error(
                "Limite de taxa: contador de reenvio da conta %s não foi gravado",
                conta.pk,
            )
