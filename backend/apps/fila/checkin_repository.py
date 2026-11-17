"""CheckinRepository: CHECKIN e TENTATIVA_CHECKIN (Fila N4 4a)."""

from datetime import date

from django.db import IntegrityError

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
