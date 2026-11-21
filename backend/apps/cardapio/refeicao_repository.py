"""RefeicaoRepository: leitura das refeições para a Exposição (N4 4a).

Só leitura. O Leitor de Cardápio (BE-12) escreve nesses models; a Exposição
nunca chama `save()` neles (um `save()` mudaria o `lida_em` da refeição).
"""

from datetime import date, timedelta

from django.db.models import Prefetch

from apps.cardapio.horario_refeicao_resolver import ORDEM_DO_DIA
from apps.cardapio.models import Campus, Categoria, FonteCardapio, Prato, Refeicao
from apps.cardapio.semana_cardapio_resolver import Semana

# Até onde procurar o próximo dia com serviço (RN05, item 5): o domingo pula
# para a segunda; um recesso longo fica "não publicado", em vez de mostrar uma
# refeição de semanas à frente.
LIMITE_PROXIMO_DIA = timedelta(days=7)

# Categorias, pratos e marcadores numa consulta por nível (4 no total), já na
# ordem do PDF: nunca uma consulta por prato (RNF01, teste de carga na BD-14).
CARDAPIO_COMPLETO = Prefetch(
    "categorias",
    queryset=Categoria.objects.order_by("ordem", "id").prefetch_related(
        Prefetch(
            "pratos",
            queryset=Prato.objects.order_by("ordem", "id").prefetch_related(
                "marcadores"
            ),
        )
    ),
)


class RefeicaoRepository:
    def buscar_refeicao(self, campus: Campus, data: date, tipo: str) -> Refeicao | None:
        """A refeição com categorias, pratos e marcadores, ou None."""
        return (
            Refeicao.objects.filter(campus=campus, data=data, tipo=tipo)
            .prefetch_related(CARDAPIO_COMPLETO)
            .first()
        )

    def refeicoes_do_dia(self, campus: Campus, data: date) -> list[Refeicao]:
        """As refeições do PDF no dia, na ordem café, almoço e jantar."""
        refeicoes = Refeicao.objects.filter(campus=campus, data=data)
        return sorted(refeicoes, key=lambda r: ORDEM_DO_DIA.index(r.tipo))

    def proximo_dia_com_servico(self, campus: Campus, depois_de: date) -> date | None:
        """O primeiro dia com refeição nos 7 dias depois de `depois_de`, ou None."""
        return (
            Refeicao.objects.filter(
                campus=campus,
                data__gt=depois_de,
                data__lte=depois_de + LIMITE_PROXIMO_DIA,
            )
            .order_by("data")
            .values_list("data", flat=True)
            .first()
        )

    def existe_cardapio_publicado(self, campus: Campus, semana: Semana) -> bool:
        """Publicado = existe a linha da `FonteCardapio` da semana (decisão de
        21/11/2026). As refeições sozinhas não bastam."""
        return FonteCardapio.objects.filter(
            campus=campus, semana_inicio=semana.inicio
        ).exists()
