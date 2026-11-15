"""PontuacaoService (Gamificação N4).

Versão mínima criada na BE-05: só `inicializar_conta`, chamada pelo cadastro
na mesma transação. A BE-14 acrescenta os outros métodos
(`registrar_contribuicao`, `apagar_contadores`...) sem mudar a assinatura de
`inicializar_conta`.
"""

from apps.gamificacao.models import PontuacaoUsuario


class PontuacaoService:
    def inicializar_conta(self, conta) -> None:
        """Cria a `PontuacaoUsuario` da conta nova, com zero ponto.

        Assim a trava da pontuação (`select_for_update`) sempre encontra a
        linha (Cadastro N4 4a, Gamificação N4).
        """
        PontuacaoUsuario.objects.create(usuario=conta)
