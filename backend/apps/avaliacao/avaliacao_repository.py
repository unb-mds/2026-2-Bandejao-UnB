"""AvaliacaoRepository: AVALIACAO (Avaliação N4 4a e 4b).

As três consultas públicas (`listar_por_refeicao`, `media_e_quantidade` e
`resumos_do_dia`) ignoram as avaliações ocultas pela moderação (RNF08,
ADR 0004): elas continuam gravadas, só não aparecem.
"""

from dataclasses import dataclass
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q

from apps.avaliacao.models import Avaliacao
from apps.cardapio.horario_refeicao_resolver import ORDEM_DO_DIA
from apps.cardapio.models import Campus, Refeicao

VISIVEL = Q(oculta=False)


@dataclass(frozen=True)
class ResumoAvaliacoes:
    """Nota média (None sem avaliações) e quantidade de uma refeição."""

    media: float | None
    quantidade: int


@dataclass(frozen=True)
class ResumoRefeicao:
    """Uma refeição no resumo do dia (RF20.3)."""

    refeicao_id: int
    tipo: str
    media: float | None
    quantidade: int


class AvaliacaoJaExisteError(Exception):
    """A inserção bateu no UNIQUE (conta, refeição): outra requisição gravou
    antes. Quem chama edita a avaliação que já existe."""


def _como_float(media) -> float | None:
    # No MySQL o AVG de inteiros volta Decimal, que o contrato não aceita.
    return None if media is None else float(media)


class AvaliacaoRepository:
    def buscar_por_conta_e_refeicao(
        self, conta, refeicao: Refeicao, travar: bool = False
    ) -> Avaliacao | None:
        """A avaliação da conta na refeição, oculta ou não, ou None.

        Com `travar`, trava a linha até o fim da transação de quem chama
        (`select_for_update`): duas edições simultâneas não se atropelam.
        """
        avaliacoes = Avaliacao.objects.filter(usuario=conta, refeicao=refeicao)
        if travar:
            avaliacoes = avaliacoes.select_for_update()
        return avaliacoes.first()

    def inserir(self, avaliacao: Avaliacao) -> Avaliacao:
        """Grava uma avaliação nova. O UNIQUE do banco é a garantia final do
        "uma por conta e refeição" (RF15.1).

        O bloco atômico próprio desfaz só a inserção, e a transação de quem
        chama continua utilizável. Se a `IntegrityError` não foi o UNIQUE
        (não existe avaliação da conta na refeição), ela sobe como veio.
        """
        try:
            with transaction.atomic():
                avaliacao.save(force_insert=True)
        except IntegrityError as erro:
            existe = Avaliacao.objects.filter(
                usuario=avaliacao.usuario, refeicao=avaliacao.refeicao
            ).exists()
            if not existe:
                raise
            raise AvaliacaoJaExisteError from erro
        return avaliacao

    def salvar_edicao(self, avaliacao: Avaliacao) -> Avaliacao:
        """Grava só nota, comentário e `editada_em`.

        `pontos_concedidos_em` é da Gamificação (ADR 0011) e `oculta` é da
        equipe (ADR 0004): gravar a linha inteira de volta poderia desfazer
        uma mudança feita neles entre a leitura e a gravação.
        """
        avaliacao.save(update_fields=("nota", "comentario", "editada_em"))
        return avaliacao

    def listar_por_refeicao(self, refeicao: Refeicao) -> list[Avaliacao]:
        """As avaliações visíveis, da mais nova para a mais antiga.

        Uma consulta só, já com o apelido do autor, e sem ler matrícula/SIAPE
        nem e-mail da conta (RI10).
        """
        return list(
            Avaliacao.objects.filter(VISIVEL, refeicao=refeicao)
            .select_related("usuario")
            .only(
                "nota",
                "comentario",
                "criada_em",
                "usuario__apelido",
            )
            .order_by("-criada_em", "-id")
        )

    def media_e_quantidade(self, refeicao: Refeicao) -> ResumoAvaliacoes:
        resumo = Avaliacao.objects.filter(VISIVEL, refeicao=refeicao).aggregate(
            media=Avg("nota"), quantidade=Count("id")
        )
        return ResumoAvaliacoes(
            media=_como_float(resumo["media"]), quantidade=resumo["quantidade"]
        )

    def resumos_do_dia(self, campus: Campus, data: date) -> list[ResumoRefeicao]:
        """Média e quantidade de cada refeição do dia, numa consulta agrupada.

        Refeição sem avaliação visível entra com média None e quantidade 0. A
        ordem é a do Anexo A (café, almoço, jantar).
        """
        visiveis = Q(avaliacoes__oculta=False)
        linhas = (
            Refeicao.objects.filter(campus=campus, data=data)
            .annotate(
                media=Avg("avaliacoes__nota", filter=visiveis),
                quantidade=Count("avaliacoes", filter=visiveis),
            )
            .values("id", "tipo", "media", "quantidade")
        )
        resumos = [
            ResumoRefeicao(
                refeicao_id=linha["id"],
                tipo=linha["tipo"],
                media=_como_float(linha["media"]),
                quantidade=linha["quantidade"],
            )
            for linha in linhas
        ]
        return sorted(resumos, key=lambda resumo: ORDEM_DO_DIA.index(resumo.tipo))
