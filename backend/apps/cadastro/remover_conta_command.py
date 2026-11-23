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

Premissa: as sessões ficam no mesmo banco da conta (`SESSION_ENGINE` fixado em
`db` no `settings.py`). É por isso que o rollback desfaz também o fim das
sessões; com cache ou cookie assinado, nada as encerraria nem as restauraria.
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
        pedido, por exemplo), registra no log e devolve False sem erro.

        Conta sem `pk` (um `AnonymousUser` ou uma conta nunca salva) é erro de
        quem chama, não "conta já excluída": levanta `ValueError`.

        Se qualquer passo falhar, nenhum vale: a transação desfaz tudo, inclusive
        as sessões, que ficam no mesmo banco (ver a premissa no topo).
        """
        if conta.pk is None:
            raise ValueError("RemoverContaCommand recebeu conta sem pk")
        conta_id = conta.pk
        with transaction.atomic():
            # Trava a linha de USUARIO (no MySQL; o SQLite ignora o
            # `select_for_update`, e os testes não cobrem a espera entre duas
            # conexões): um login concorrente espera e depois não acha a conta, e
            # um segundo pedido de exclusão devolve False. O check-in não trava
            # a linha: ele só espera, por efeito da checagem de FK do InnoDB, e
            # depois recebe um erro de integridade, em vez de ver a conta apagada.
            existente = (
                get_user_model().objects.select_for_update().filter(pk=conta_id).first()
            )
            if existente is None:
                logger.info("Exclusão da conta %s ignorada: já não existe", conta_id)
                return False
            self.pontuacao_service.apagar_contadores(existente)
            registros = self.retencao_fila_service.desvincular_conta(existente)
            sessoes = self.sessoes_da_conta.encerrar_todas(existente)
            self.conta_repository.excluir(existente)
            # Só depois do commit de verdade: se este `atomic` for um savepoint
            # dentro de outra transação (um decorador, `ATOMIC_REQUESTS`) que
            # desfizer, o log não diz que excluiu o que continua no banco. Só o
            # id e as contagens: nada de matrícula, e-mail nem apelido (RNF07).
            transaction.on_commit(
                lambda: logger.info(
                    "Conta %s excluída: %s sessões, %s registros de fila desvinculados",
                    conta_id,
                    sessoes,
                    registros,
                )
            )
        return True
