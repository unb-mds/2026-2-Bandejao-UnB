"""SessoesDaConta: a sessão do Django em cookie HttpOnly (ADR 0007, Cadastro N4 4c).

Não é uma tabela do projeto: é o `django.contrib.sessions` (`django_session`)
com o `login`/`logout` do Django. `encerrar_todas(conta)` entra com a
redefinição de senha (RF04) e a exclusão de conta (BD-12).
"""

from django.contrib.auth import SESSION_KEY, login, logout
from django.contrib.sessions.models import Session

from apps.cadastro.models import Usuario


class SessoesDaConta:
    def abrir(self, request, conta: Usuario) -> None:
        """Abre a sessão da conta.

        O Django troca o id da sessão (evita fixação de sessão) e o token CSRF:
        o PWA precisa ler o cookie `csrftoken` de novo depois do login.
        """
        login(request, conta)

    def encerrar_atual(self, request) -> None:
        """Apaga só a sessão desta requisição (RF03.3): outros aparelhos seguem logados."""
        logout(request)

    def encerrar_todas(self, conta: Usuario) -> int:
        """Apaga as sessões de todos os aparelhos da conta e devolve quantas
        eram (exclusão de conta, BD-12; redefinição de senha, RF04).

        A sessão do Django não tem coluna da conta: o id dela está dentro dos
        dados da sessão. Por isso o laço olha cada sessão (as expiradas
        também, que o `clearsessions` ainda não apagou), o que é barato no
        volume do projeto. Uma sessão ilegível é de visitante ou de dado
        antigo e é ignorada.
        """
        alvo = str(conta.pk)
        chaves = [
            sessao.session_key
            for sessao in Session.objects.all().iterator()
            if sessao.get_decoded().get(SESSION_KEY) == alvo
        ]
        if chaves:
            Session.objects.filter(session_key__in=chaves).delete()
        return len(chaves)
