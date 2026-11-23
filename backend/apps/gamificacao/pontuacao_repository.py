"""PontuacaoRepository: PONTUACAO_USUARIO e PONTOS_SEMESTRE_CAMPUS
(Gamificação N4 4a, ADR 0011)."""

from django.db import IntegrityError, transaction
from django.db.models import Case, Exists, OuterRef, QuerySet, Value, When

from apps.cadastro.models import StatusUsuario
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

    def apagar_da_conta(self, conta) -> None:
        """Apaga os pontos de cada semestre e campus e a pontuação total da
        conta (BD-12). Os pontos por semestre saem primeiro; as duas tabelas
        apontam para a conta, e nenhuma aponta para a outra."""
        PontosSemestreCampus.objects.filter(usuario=conta).delete()
        PontuacaoUsuario.objects.filter(usuario=conta).delete()

    def alterar_adesao(self, conta, participa: bool) -> None:
        """Liga ou desliga a adesão ao ranking (RF27.1, Gamificação N4 4c).

        Abre a própria transação: o projeto não usa `ATOMIC_REQUESTS`, e o
        `select_for_update` de `travar_por_conta` precisa de uma. Reaproveitar
        a trava cria a linha que falta e mantém a ordem de travas da BE-14
        (conta primeiro).

        Grava só `participa_ranking` (e o `atualizado_em` da `PontuacaoUsuario`,
        que o ranking não usa), assim como `salvar` grava só os pontos: um
        não apaga o que o outro gravou. Não toca na `PontosSemestreCampus`,
        cujo `atualizado_em` é o desempate do ranking. Idempotente, e os
        pontos continuam somando com a adesão desligada.
        """
        with transaction.atomic():
            pontuacao = self.travar_por_conta(conta)
            pontuacao.participa_ranking = participa
            pontuacao.save(update_fields=["participa_ranking", "atualizado_em"])

    def elegiveis(self, campus: Campus, semestre: str) -> QuerySet:
        """As linhas do ranking do campus no semestre, em ordem (RN12): só
        quem aderiu, com conta ativa e ao menos 1 ponto, pelos pontos e com
        desempate por quem pontuou antes (`atualizado_em` mais antigo).

        Devolve a consulta sem corte, para quem chama pôr o `LIMIT`. A forma
        é a do BD-10 (docs/arquitetura/banco-de-dados/indices-bd10.md): a
        adesão e a conta ativa num `EXISTS` dentro de um `CASE`, com `alias`,
        sem join nem `select_related`, e a ordem exatamente
        `-pontos, atualizado_em`. Só assim o MySQL 8.4 lê o índice do ranking
        já em ordem, sem ordenar em arquivo temporário.
        """
        elegivel = Exists(
            PontuacaoUsuario.objects.filter(
                usuario_id=OuterRef("usuario_id"),
                participa_ranking=True,
                usuario__status=StatusUsuario.ATIVO,
            )
        )
        return (
            PontosSemestreCampus.objects.filter(
                campus=campus, semestre_referencia=semestre, pontos__gte=1
            )
            # `alias` e não `annotate`: a subconsulta fica só no WHERE.
            .alias(
                elegivel=Case(When(elegivel, then=Value(True)), default=Value(False))
            )
            .filter(elegivel=True)
            .order_by("-pontos", "atualizado_em")
        )

    @staticmethod
    def _ler_com_trava(conta) -> PontuacaoUsuario | None:
        return (
            PontuacaoUsuario.objects.select_for_update().filter(usuario=conta).first()
        )
