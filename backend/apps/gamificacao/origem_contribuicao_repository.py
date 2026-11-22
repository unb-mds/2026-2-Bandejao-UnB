"""OrigemContribuicaoRepository: os registros que geram pontos (Gamificação N4 4a).

A Gamificação só LÊ os models da Fila e da Avaliação e só ESCREVE neles o
marcador `pontos_concedidos_em` (ADR 0011). O contrário (Fila ou Avaliação
mexendo em contador) não pode.

Todas as consultas vão ao banco na hora, sem reaproveitar objeto carregado
antes: o `PontuacaoService` as faz depois da trava por conta, e é isso que, no
READ COMMITTED, deixa ver o que a outra transação acabou de gravar.
"""

from datetime import datetime

from apps.avaliacao.models import Avaliacao
from apps.fila.models import Checkin, PerguntaSaida
from apps.gamificacao.contribuicao import RefeicaoRef, TipoContribuicao

# Onde fica o marcador de cada tipo. O da resposta de saída fica na pergunta.
MODELO_DA_ORIGEM = {
    TipoContribuicao.CHECKIN: Checkin,
    TipoContribuicao.AVALIACAO: Avaliacao,
    TipoContribuicao.RESPOSTA_SAIDA: PerguntaSaida,
}


class OrigemContribuicaoRepository:
    def ja_pontuada(self, tipo: TipoContribuicao, origem_id: int) -> bool:
        """Lê o marcador no banco, nunca no objeto de quem chamou."""
        return (
            MODELO_DA_ORIGEM[tipo]
            .objects.filter(id=origem_id, pontos_concedidos_em__isnull=False)
            .exists()
        )

    def marcar_pontuada(
        self, tipo: TipoContribuicao, origem_id: int, agora: datetime
    ) -> bool:
        """Grava o marcador e diz se gravou: False quando o registro não existe,
        é de outro tipo ou já tinha o marcador.

        Grava só o marcador, sem carregar a linha: um `save()` da linha
        inteira desfaria uma edição ou ocultação feita no meio do caminho.
        """
        marcadas = (
            MODELO_DA_ORIGEM[tipo]
            .objects.filter(id=origem_id, pontos_concedidos_em__isnull=True)
            .update(pontos_concedidos_em=agora)
        )
        return marcadas == 1

    def tem_checkin_confirmado(self, conta, refeicao: RefeicaoRef) -> bool:
        """Mesma refeição é campus + tipo + data, nunca o conteúdo do cardápio.

        Só existe check-in confirmado na tabela `Checkin`; os recusados ficam
        em `TentativaCheckin`.
        """
        return Checkin.objects.filter(
            usuario=conta,
            campus=refeicao.campus,
            tipo_refeicao=refeicao.tipo_refeicao,
            data=refeicao.data,
        ).exists()

    def avaliacao_nao_pontuada(self, conta, refeicao: RefeicaoRef) -> Avaliacao | None:
        """A avaliação da conta na refeição que ainda não pontuou (feita antes
        do check-in), ou None. A ocultada pela moderação não pontua."""
        return Avaliacao.objects.filter(
            usuario=conta,
            refeicao__campus=refeicao.campus,
            refeicao__tipo=refeicao.tipo_refeicao,
            refeicao__data=refeicao.data,
            pontos_concedidos_em__isnull=True,
            oculta=False,
        ).first()

    def avaliacao_oculta(self, origem_id: int) -> bool:
        """Avaliação ocultada pela moderação (ADR 0004) não pontua."""
        return Avaliacao.objects.filter(id=origem_id, oculta=True).exists()
