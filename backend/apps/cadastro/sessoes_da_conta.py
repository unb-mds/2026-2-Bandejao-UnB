"""SessoesDaConta: a sessão do Django em cookie HttpOnly (ADR 0007, Cadastro N4 4c).

Não é uma tabela do projeto: é o `django.contrib.sessions` (`django_session`)
com o `login`/`logout` do Django. `encerrar_todas(conta)` entra com a
redefinição de senha (RF04) e a exclusão de conta (BD-12).
"""

from django.contrib.auth import login, logout

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
