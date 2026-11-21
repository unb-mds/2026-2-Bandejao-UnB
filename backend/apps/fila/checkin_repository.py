"""CheckinRepository: CHECKIN e TENTATIVA_CHECKIN (Fila N4 4a)."""

from datetime import date

from django.db import IntegrityError
from django.db.models import Q

from apps.cardapio.models import Campus
from apps.fila.erros import CheckinDuplicadoError
from apps.fila.models import Checkin, TentativaCheckin


class CheckinRepository:
    def existe_checkin(
        self, conta, campus: Campus, tipo_refeicao: str, data: date
    ) -> bool:
        return Checkin.objects.filter(
            usuario=conta, campus=campus, tipo_refeicao=tipo_refeicao, data=data
        ).exists()

    def salvar_checkin(self, checkin: Checkin) -> Checkin:
        """Grava o check-in. O UNIQUE do banco é a garantia final do RI03.

        Duas requisições simultâneas (duplo toque) passam juntas pelo
        `existe_checkin`; a segunda bate no UNIQUE e vira
        `CheckinDuplicadoError`. Quem chama abre a `transaction.atomic()`: a
        `IntegrityError` desfaz só aquele bloco.

        Toda `IntegrityError` vira duplicidade porque o UNIQUE é a única
        constraint de CHECKIN que um pedido válido consegue violar. Se entrar
        outra (um `CheckConstraint`, por exemplo), separe os casos aqui, senão
        a violação dela grava uma tentativa com o motivo errado.
        """
        try:
            checkin.save(force_insert=True)
        except IntegrityError as erro:
            raise CheckinDuplicadoError from erro
        return checkin

    def registrar_tentativa(self, tentativa: TentativaCheckin) -> None:
        tentativa.save(force_insert=True)

    def desvincular_antes_de(self, data: date) -> int:
        """Retenção (RNF07.3, Fila N4 4d): retira a conta e a hora exata dos
        registros com `data` anterior a `data`. Devolve quantos mudaram.

        Só conta o que ainda tinha conta ou hora, então rodar de novo devolve 0.
        """
        return self._desvincular(
            Checkin.objects.filter(data__lt=data),
            TentativaCheckin.objects.filter(data__lt=data),
        )

    def desvincular_conta(self, conta) -> int:
        """Exclusão de conta (RNF07.4): retira a conta e a hora exata de todos os
        registros dela, inclusive os de hoje. Devolve quantos mudaram."""
        return self._desvincular(
            Checkin.objects.filter(usuario=conta),
            TentativaCheckin.objects.filter(usuario=conta),
        )

    @staticmethod
    def _desvincular(checkins, tentativas) -> int:
        """Anula a conta e a hora; campus, tipo, data, faixa, tempo de espera e
        marcador de pontos ficam para a previsão (RF13, RF22). Um UPDATE por
        tabela, sem carregar as linhas. O UNIQUE de CHECKIN aceita várias linhas
        com a conta nula (NULL não colide no SQLite nem no MySQL)."""
        alterados = checkins.filter(
            Q(usuario__isnull=False) | Q(registrado_em__isnull=False)
        ).update(usuario=None, registrado_em=None)
        alterados += tentativas.filter(
            Q(usuario__isnull=False) | Q(data_hora__isnull=False)
        ).update(usuario=None, data_hora=None)
        return alterados
