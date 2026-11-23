"""CheckinRepository: CHECKIN e TENTATIVA_CHECKIN (Fila N4 4a, 4c e 4d)."""

from dataclasses import dataclass
from datetime import date, time

from django.db import IntegrityError
from django.db.models import Count, Q

from apps.cardapio.models import Campus
from apps.fila.erros import CheckinDuplicadoError
from apps.fila.faixa_horario_generator import FaixaHorario
from apps.fila.models import Checkin, TentativaCheckin


@dataclass(frozen=True)
class ContagemDia:
    """Check-ins de um dia da janela, um número por faixa, na ordem das faixas."""

    data: date
    checkins_por_faixa: list[int]


def _posicao_da_faixa(faixa_inicio: time, faixas: list[FaixaHorario]) -> int | None:
    """Em que faixa cai o `faixa_inicio` gravado no check-in, ou None.

    O check-in vale até o fim da refeição inclusive (`JanelaCheckinValidator`):
    o feito às 14h30 tem faixa 14h30, que é o fim da última faixa, e entra
    nela. Fora disso, só cai fora se o horário do Anexo A mudou depois.
    """
    for posicao, faixa in enumerate(faixas):
        if faixa.inicio <= faixa_inicio < faixa.fim:
            return posicao
    if faixas and faixa_inicio == faixas[-1].fim:
        return len(faixas) - 1
    return None


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

    def contar_por_faixa(
        self,
        campus: Campus,
        tipo_refeicao: str,
        datas: list[date],
        faixas: list[FaixaHorario],
    ) -> list[ContagemDia]:
        """Check-ins por dia e faixa da previsão (RF13, Fila N4 4c).

        Devolve só os dias com dados (pelo menos um check-in nas faixas), na
        ordem de `datas`; nesses dias, a faixa sem check-in vem com zero.
        Conta também os check-ins que já perderam a conta na retenção.

        Uma consulta só, agrupada no banco, com a forma conferida pela BD-10:
        igualdade em campus e tipo e `IN` nas datas, que usa o
        `checkin_campus_tipo_data_idx` (docs/arquitetura/banco-de-dados/
        indices-bd10.md). Não mude os filtros sem rodar aquele teste.
        """
        linhas = (
            Checkin.objects.filter(
                campus=campus, tipo_refeicao=tipo_refeicao, data__in=datas
            )
            .values("data", "faixa_inicio")
            .annotate(quantidade=Count("id"))
            .order_by()
        )
        por_dia: dict[date, list[int]] = {}
        for linha in linhas:
            posicao = _posicao_da_faixa(linha["faixa_inicio"], faixas)
            if posicao is None:
                continue
            contagem = por_dia.setdefault(linha["data"], [0] * len(faixas))
            contagem[posicao] += linha["quantidade"]
        return [
            ContagemDia(data=data, checkins_por_faixa=por_dia[data])
            for data in datas
            if data in por_dia
        ]

    def desvincular_antes_de(self, limite: date) -> int:
        """Retenção (RNF07.3, Fila N4 4d): desvincula os registros com `data`
        anterior a `limite`; o próprio dia `limite` fica de fora. Devolve
        quantos mudaram.

        Conta o que ainda tinha conta ou hora, então rodar de novo devolve 0.
        """
        return self._desvincular(
            Checkin.objects.filter(data__lt=limite),
            TentativaCheckin.objects.filter(data__lt=limite),
        )

    def desvincular_conta(self, conta) -> int:
        """Exclusão de conta (RNF07.4): desvincula todos os registros da conta,
        inclusive os de hoje. Devolve quantos mudaram."""
        return self._desvincular(
            Checkin.objects.filter(usuario=conta),
            TentativaCheckin.objects.filter(usuario=conta),
        )

    @staticmethod
    def _desvincular(checkins, tentativas) -> int:
        """Anula a conta, `Checkin.registrado_em` e `TentativaCheckin.data_hora`.

        Campus, tipo, data, faixa e tempo de espera ficam para a previsão
        (RF13, RF22); o marcador de pontos fica para a gamificação (ADR 0011);
        na tentativa, ficam também resultado e motivo. Outros horários
        (`pontos_concedidos_em` e os da pergunta e da resposta de saída)
        ficam, sem conta (C4 da Fila, 4d).

        O filtro pega também o registro sem conta e com hora, que sobra
        quando a conta é apagada sem passar pelo `desvincular_conta` (o
        `SET_NULL` anula só a conta). Um UPDATE por tabela, sem carregar as
        linhas; quem chama abre a transação, para as duas tabelas mudarem
        juntas. Com a conta nula, o UNIQUE de CHECKIN não restringe nada
        (NULL não colide no SQLite nem no MySQL)."""
        alterados = checkins.filter(
            Q(usuario__isnull=False) | Q(registrado_em__isnull=False)
        ).update(usuario=None, registrado_em=None)
        alterados += tentativas.filter(
            Q(usuario__isnull=False) | Q(data_hora__isnull=False)
        ).update(usuario=None, data_hora=None)
        return alterados
