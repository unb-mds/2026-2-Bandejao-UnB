"""PontuacaoRepository: PONTUACAO_USUARIO e PONTOS_SEMESTRE_CAMPUS
(Gamificação N4 4a, ADR 0011)."""

from django.db import IntegrityError, transaction

from apps.cardapio.models import Campus
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario


class PontuacaoRepository:
    def travar_por_conta(self, conta) -> PontuacaoUsuario:
        """A `PontuacaoUsuario` da conta, travada até o fim da transação de
        quem chama (`select_for_update`).

        A trava é a catraca da conta: as contribuições da mesma conta passam
        uma de cada vez. Tem de ser a primeira leitura da pontuação.

        A linha nasce com a conta (BE-05, BD-03). Se mesmo assim faltar, é
        criada com zero ponto num savepoint: se outra requisição a criar ao
        mesmo tempo, o UNIQUE desfaz só a criação e a linha da outra é lida
        de novo, com trava. Se a `IntegrityError` não foi o UNIQUE (a linha
        continua sem existir), ela sobe como veio.
        """
        pontuacao = self._ler_com_trava(conta)
        if pontuacao is not None:
            return pontuacao
        try:
            with transaction.atomic():
                return PontuacaoUsuario.objects.create(usuario=conta)
        except IntegrityError:
            pontuacao = self._ler_com_trava(conta)
            if pontuacao is None:
                raise
            return pontuacao

    def somar_pontos_semestre(
        self, conta, campus: Campus, semestre: str, pontos: int
    ) -> None:
        """Soma `pontos` à linha da conta no campus e semestre, criando-a se
        faltar.

        Carrega e salva em vez de `.update()`: o `update()` não dispara o
        `auto_now` do `atualizado_em`, que é o desempate do ranking. A trava
        por conta já serializa as gravações da mesma conta. Quem chama só
        chama quando a pessoa ganha ponto.
        """
        linha, _ = PontosSemestreCampus.objects.get_or_create(
            usuario=conta, campus=campus, semestre_referencia=semestre
        )
        linha.pontos += pontos
        linha.save(update_fields=["pontos", "atualizado_em"])

    def salvar(self, pontuacao: PontuacaoUsuario) -> None:
        """Grava os pontos totais (e o `atualizado_em`, pelo `auto_now`)."""
        pontuacao.save(update_fields=["pontos_totais", "atualizado_em"])

    @staticmethod
    def _ler_com_trava(conta) -> PontuacaoUsuario | None:
        return (
            PontuacaoUsuario.objects.select_for_update().filter(usuario=conta).first()
        )
