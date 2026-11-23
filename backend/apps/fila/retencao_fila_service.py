"""RetencaoFilaService: retenção de 4 semanas dos registros de fila (BD-11).

Fila N4 (4d), RNF07.3 e RNF07.4. Depois do prazo, `Checkin` e
`TentativaCheckin` perdem a conta, `registrado_em` e `data_hora`, e continuam
servindo à previsão de pico. A `PerguntaSaida` e a `RespostaSaida` não guardam
a conta: chegam a ela pelo check-in e perdem o vínculo junto; os horários
delas e o `pontos_concedidos_em` do check-in ficam, sem conta.
"""

from datetime import date, timedelta

from django.db import transaction

from apps.fila.checkin_repository import CheckinRepository
from config.parametros import ParametrosFilaConfig


class RetencaoFilaService:
    def __init__(self, repository: CheckinRepository | None = None):
        self.repository = repository or CheckinRepository()

    def desvincular_antigos(self, hoje: date) -> int:
        """Desvincula o que tem `data` anterior a 4 semanas antes de `hoje`.

        O dia-limite fica: com `hoje` em 21/11, o check-in de 24/10 ainda é
        da conta e o de 23/10 deixa de ser. `hoje` é o dia de Brasília, quem
        chama decide (o job usa `timezone.localdate()`). As duas tabelas
        mudam na mesma transação.
        """
        limite = hoje - timedelta(weeks=ParametrosFilaConfig.retencao_semanas)
        with transaction.atomic():
            return self.repository.desvincular_antes_de(limite)

    def desvincular_conta(self, conta) -> int:
        """Desvincula todos os registros de fila da conta. Será chamado pelo
        `RemoverContaCommand` (BD-12, #164), dentro da transação dele."""
        with transaction.atomic():
            return self.repository.desvincular_conta(conta)
