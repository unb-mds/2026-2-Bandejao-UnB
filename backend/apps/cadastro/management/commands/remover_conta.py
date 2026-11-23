"""`python manage.py remover_conta <conta_id>` (RNF07.4, BD-12, Cadastro N4 4d).

É o jeito de a equipe excluir uma conta a pedido da pessoa (LGPD): o comando
chama o `RemoverContaCommand`, que apaga os contadores, desvincula a fila,
encerra as sessões e apaga a linha de USUARIO numa transação só. Excluir por
SQL deixaria de fora esses passos e as regras do ORM (ADR 0004 revisada).

O id é o da conta (`USUARIO.id`). A saída e o log levam só esse id, nunca
matrícula, e-mail ou apelido (RNF07).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.cadastro.remover_conta_command import RemoverContaCommand


class Command(BaseCommand):
    help = "Exclui a conta pelo id, a pedido da pessoa (RNF07.4, LGPD)."

    def add_arguments(self, parser):
        parser.add_argument("conta_id", type=int, help="id da conta (USUARIO.id)")

    def handle(self, *args, **options):
        conta_id = options["conta_id"]
        conta = get_user_model().objects.filter(pk=conta_id).first()
        if conta is None:
            raise CommandError(f"A conta {conta_id} não existe.")
        # Uma exclusão feita ao mesmo tempo por outro processo já terá apagado
        # a conta: o comando devolve False e o resultado é o mesmo.
        if not RemoverContaCommand().executar(conta):
            raise CommandError(f"A conta {conta_id} já foi excluída.")
        self.stdout.write(f"Conta {conta_id} excluída.")
