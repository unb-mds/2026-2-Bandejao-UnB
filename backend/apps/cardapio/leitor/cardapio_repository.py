"""CardapioRepository: grava no banco o cardápio lido do PDF (Leitor N4 4b).

Analogia: é quem troca o cardápio do quadro na porta do RU. Ele troca os
pratos, mas não arranca o quadro da parede: a `Refeicao` existente é
atualizada, nunca apagada e recriada, porque `AVALIACAO.refeicao` é
`ON DELETE CASCADE` e as avaliações dela iriam junto. Categorias, pratos e
marcadores, que ninguém mais referencia, são apagados e gravados de novo.

Quem abre a transação é o `LeitorCardapioService`: a semana inteira (todas
as páginas do PDF e a `FonteCardapio`) entra junto, ou nada entra.
"""

import logging
from datetime import date

from apps.cardapio.leitor.cardapio_downloader import FontePDF
from apps.cardapio.leitor.cardapio_pdf_parser import RefeicaoEstruturada
from apps.cardapio.models import (
    Campus,
    Categoria,
    FonteCardapio,
    Marcador,
    Prato,
    Refeicao,
    StatusLeitura,
    TipoRefeicao,
)
from config.parametros import HorariosRefeicaoConfig

logger = logging.getLogger(__name__)

HORARIOS = {
    TipoRefeicao.CAFE: HorariosRefeicaoConfig.horario_cafe,
    TipoRefeicao.ALMOCO: HorariosRefeicaoConfig.horario_almoco,
    TipoRefeicao.JANTAR: HorariosRefeicaoConfig.horario_jantar,
}


class CardapioRepository:
    def salvar(
        self, campus: Campus, fonte: FontePDF, refeicao: RefeicaoEstruturada
    ) -> list[Refeicao]:
        """Grava uma página do PDF: uma `Refeicao` por dia, com status `ok`.

        A página só em texto também passa por aqui (os pratos vêm sem
        marcadores); depois o serviço chama `marcar_alergenos_indisponivel`.
        Categorias e pratos ficam na ordem do PDF (a Exposição ordena por
        `ordem`), e a categoria sem prato no dia não é gravada. A dieta da
        categoria é copiada para cada prato dela (C4 4b).
        """
        inicio, fim = HORARIOS[refeicao.refeicao]
        marcadores = {}
        gravadas = []
        for dia in refeicao.dias:
            data = date.fromisoformat(dia["data"])
            linha, _ = Refeicao.objects.update_or_create(
                campus=campus,
                data=data,
                tipo=refeicao.refeicao,
                defaults={
                    "horario_inicio": inicio,
                    "horario_fim": fim,
                    "status_leitura": StatusLeitura.OK,
                    "fonte_pdf_url": fonte.url,
                },
            )
            # Apaga as categorias antigas; pratos e PratoMarcador vão junto.
            linha.categorias.all().delete()
            for ordem, categoria in enumerate(refeicao.categorias):
                pratos = categoria.pratos_por_dia.get(dia["data"], [])
                if not pratos:
                    continue
                gravada = Categoria.objects.create(
                    refeicao=linha, nome=categoria.nome, ordem=ordem
                )
                for ordem_prato, prato in enumerate(pratos):
                    novo = Prato.objects.create(
                        categoria=gravada,
                        nome=prato.descricao,
                        dieta=categoria.dieta,
                        ordem=ordem_prato,
                    )
                    novo.marcadores.add(
                        *(self._marcador(nome, marcadores) for nome in prato.marcadores)
                    )
            gravadas.append(linha)
        return gravadas

    @staticmethod
    def _marcador(nome, cache):
        # Nome fora da fixture é erro de programação (o parser só devolve os
        # 10 do dicionário de dados): `Marcador.DoesNotExist` sobe.
        if nome not in cache:
            cache[nome] = Marcador.objects.get(nome=nome)
        return cache[nome]

    def remover_ausentes(
        self, campus: Campus, fonte: FontePDF, gravadas: list[Refeicao]
    ) -> None:
        """Apaga as refeições da semana do PDF que não estão mais nele.

        Decisão P1 (21/11/2026): o RU corrigiu o PDF e tirou uma refeição
        (ex.: o jantar de sexta). A que já tem avaliação fica, com um aviso
        no log, para nenhuma avaliação se perder. Só a semana do link
        (`fonte.inicio` a `fonte.fim`) e só o campus.
        """
        sumiram = (
            Refeicao.objects.filter(
                campus=campus, data__gte=fonte.inicio, data__lte=fonte.fim
            )
            .exclude(pk__in=[r.pk for r in gravadas])
            .order_by("data", "tipo")
        )
        for refeicao in sumiram.filter(avaliacoes__isnull=False).distinct():
            # Sem dado de usuário: só campus, data e tipo.
            logger.warning(
                "Refeição do campus %s em %s (%s) saiu do PDF corrigido, mas "
                "tem avaliação: mantida.",
                campus.pk,
                refeicao.data.isoformat(),
                refeicao.tipo,
            )
        sumiram.filter(avaliacoes__isnull=True).delete()

    def manter_ultimo_valido(self, campus: Campus, fonte: FontePDF) -> bool:
        """O PDF da semana falhou: nada no banco muda (RF06.4).

        Não toca nas refeições nem cria linha `leitura_falhou` (decisão P2):
        sem a `FonteCardapio` da semana, a Exposição já mostra "não
        publicado", e a falha fica no `ALERTA_LEITURA_CARDAPIO`. Também não
        chama `save()` (o `lida_em` é `auto_now`). Devolve se havia um
        cardápio válido da semana, para a mensagem do alerta.
        """
        return FonteCardapio.objects.filter(
            campus=campus, semana_inicio=fonte.inicio
        ).exists()

    def marcar_alergenos_indisponivel(
        self, campus: Campus, refeicao: str, data: date
    ) -> None:
        """A refeição saiu só em texto (RF06.3): o filtro de marcadores fica
        desativado para ela na Exposição (`alergenos_indisponivel`)."""
        Refeicao.objects.filter(campus=campus, data=data, tipo=refeicao).update(
            status_leitura=StatusLeitura.ALERGENOS_INDISPONIVEIS
        )
