"""RemoverContaCommand: exclusão de conta (BD-12, Cadastro N4 4d).

RNF07.4, RNF08 e ADR 0004 revisada: excluir a conta **apaga a linha** de
`USUARIO` (não existe mais o status `removido`). Tudo na mesma transação:

1. os contadores da pontuação somem (a conta sai do ranking na hora);
2. os registros de fila perdem a conta e a hora exata, de qualquer data;
3. as sessões de todos os aparelhos são encerradas;
4. a linha da conta é apagada, e o CASCADE leva os tokens. As avaliações
   ficam, sem `usuario_id` (aparecem como "usuário removido").

Matrícula/SIAPE, e-mail e apelido ficam livres para um novo cadastro. Os
backups guardam a conta por até 7 dias (BD-15).
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.sessoes_da_conta import SessoesDaConta
from apps.fila.retencao_fila_service import RetencaoFilaService
from apps.gamificacao.pontuacao_service import PontuacaoService

logger = logging.getLogger(__name__)


class RemoverContaCommand:
    def __init__(self):
        self.conta_repository = ContaRepository()
        self.pontuacao_service = PontuacaoService()
        self.retencao_fila_service = RetencaoFilaService()
        self.sessoes_da_conta = SessoesDaConta()

    def executar(self, conta) -> bool:
        """Exclui a conta e devolve True. Se ela já não existe (um segundo
        pedido, por exemplo), devolve False sem erro.

        Se qualquer passo falhar, nenhum vale: a transação desfaz tudo, inclusive
        as sessões, que ficam no mesmo banco.
        """
        with transaction.atomic():
            # Trava a linha: um check-in ou um login no meio da exclusão espera
            # e depois vê a conta já apagada.
            existente = (
                get_user_model().objects.select_for_update().filter(pk=conta.pk).first()
            )
            if existente is None:
                return False
            self.pontuacao_service.apagar_contadores(existente)
            self.retencao_fila_service.desvincular_conta(existente)
            self.sessoes_da_conta.encerrar_todas(existente)
            self.conta_repository.excluir(existente)
        # Só o id: o log não leva matrícula, e-mail nem apelido (RNF07).
        logger.info("Conta %s excluída", conta.pk)
        return True
