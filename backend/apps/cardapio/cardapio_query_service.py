"""CardapioQueryService: monta o cardápio filtrado de uma refeição (N4 4a).

Analogia: é o maître. Ele não cozinha nem decide o horário sozinho; pergunta
ao relógio da entrada (HorarioRefeicaoResolver) qual refeição servir, ao
calendário (SemanaCardapioResolver) se a semana já saiu, à despensa
(RefeicaoRepository) o que tem, e passa o prato por dois garçons: primeiro o
da dieta (que tira travessas), depois o do marcador (que só sinaliza).
"""

from datetime import date, datetime

from django.utils import timezone

from apps.cardapio.cardapio_filtrado import CardapioFiltrado, StatusCardapio
from apps.cardapio.dieta_selecionada import DietaSelecionada
from apps.cardapio.filtro_dieta_service import FiltroDietaService
from apps.cardapio.filtro_marcador_service import FiltroMarcadorService
from apps.cardapio.horario_refeicao_resolver import (
    ORDEM_DO_DIA,
    HorarioRefeicaoResolver,
    RefeicaoPadrao,
    refeicao_terminou,
)
from apps.cardapio.models import Campus, Refeicao, StatusLeitura
from apps.cardapio.refeicao_repository import RefeicaoRepository
from apps.cardapio.semana_cardapio_resolver import (
    DURACAO_SEMANA,
    SemanaCardapioResolver,
)


def dia_pedido(semana: date | None, dia: date | None, hoje: date) -> date:
    """O dia a partir do qual a RN05 é aplicada.

    `dia` vale se veio. Sem ele, o dia corrente, a não ser que a `semana`
    pedida não contenha hoje: aí, o primeiro dia dela.
    """
    if dia is not None:
        return dia
    if semana is not None and not semana <= hoje <= semana + DURACAO_SEMANA:
        return semana
    return hoje


class CardapioQueryService:
    def __init__(self):
        self.repositorio = RefeicaoRepository()
        self.horarios = HorarioRefeicaoResolver()
        self.semanas = SemanaCardapioResolver()
        self.filtro_dieta = FiltroDietaService()
        self.filtro_marcador = FiltroMarcadorService()

    def obter_cardapio(
        self,
        campus: Campus,
        semana: date | None,
        dia: date | None,
        refeicao: str | None,
        marcadores_selecionados: list[str],
        dieta: DietaSelecionada,
        *,
        agora: datetime,
    ) -> CardapioFiltrado:
        """Cardápio de uma refeição de um dia, já filtrado (RF07, RF08, RF09).

        `agora` é o instante da requisição, lido uma vez só na view.
        `semana` e `dia` já validados (o dia, se veio, está na semana).
        """
        inicio = dia_pedido(semana, dia, timezone.localtime(agora).date())
        if refeicao is not None:
            padrao = RefeicaoPadrao(
                refeicao=refeicao,
                dia=inicio,
                encerrada=refeicao_terminou(agora, inicio, refeicao),
            )
        else:
            padrao = self._refeicao_padrao(campus, inicio, agora)

        if padrao is None:
            # Nenhum dia com serviço de `inicio` em diante: nada publicado a
            # mostrar. A refeição vem só dos horários do Anexo A.
            sem_pdf = [Refeicao(data=inicio, tipo=tipo) for tipo in ORDEM_DO_DIA]
            return self._nao_publicado(
                campus, self.horarios.refeicao_padrao(agora, sem_pdf)
            )
        if not self._publicado(campus, padrao.dia):
            return self._nao_publicado(campus, padrao)

        encontrada = self.repositorio.buscar_refeicao(
            campus, padrao.dia, padrao.refeicao
        )
        if encontrada and encontrada.status_leitura == StatusLeitura.LEITURA_FALHOU:
            # Linha criada sem cardápio anterior válido (N4 do banco): não há
            # o que mostrar (RF06.4). Publicada, ela sairia com o filtro de
            # marcador ativo e sem nada sinalizado, como se fosse segura.
            return self._nao_publicado(campus, padrao)
        alergenos_indisponivel = bool(encontrada and encontrada.alergenos_indisponivel)
        categorias = []
        if encontrada is not None:
            # A ordem importa: a dieta pode tirar categorias inteiras, e o
            # marcador só avalia o que sobrou.
            categorias = self.filtro_marcador.aplicar(
                self.filtro_dieta.aplicar(encontrada, dieta),
                marcadores_selecionados,
                alergenos_indisponivel,
            )
        return CardapioFiltrado(
            campus=campus,
            refeicao=padrao.refeicao,
            data=padrao.dia,
            refeicao_encerrada=padrao.encerrada,
            status=StatusCardapio.PUBLICADO,
            alergenos_indisponivel=alergenos_indisponivel,
            filtro_marcador_desativado=alergenos_indisponivel,
            categorias=categorias,
        )

    def _refeicao_padrao(
        self, campus: Campus, inicio: date, agora: datetime
    ) -> RefeicaoPadrao | None:
        """RN05: a padrão do dia ou, sem serviço nele, a do próximo dia com
        serviço (item 5). None se não há dia com serviço de `inicio` em diante.
        """
        refeicoes = self.repositorio.refeicoes_do_dia(campus, inicio)
        if not refeicoes:
            proximo = self.repositorio.proximo_dia_com_servico(campus, inicio)
            if proximo is None:
                return None
            refeicoes = self.repositorio.refeicoes_do_dia(campus, proximo)
        return self.horarios.refeicao_padrao(agora, refeicoes)

    def _publicado(self, campus: Campus, dia: date) -> bool:
        """A semana do dia exibido tem a linha da FonteCardapio (RF18)."""
        vigente = next(
            (s for s in self.semanas.semanas_disponiveis(campus, dia) if s.vigente),
            None,
        )
        return vigente is not None and self.repositorio.existe_cardapio_publicado(
            campus, vigente
        )

    @staticmethod
    def _nao_publicado(campus: Campus, padrao: RefeicaoPadrao) -> CardapioFiltrado:
        # Volta 200, nunca 404 (RF18, RF07.3), com o aviso e sem categorias.
        return CardapioFiltrado(
            campus=campus,
            refeicao=padrao.refeicao,
            data=padrao.dia,
            refeicao_encerrada=padrao.encerrada,
            status=StatusCardapio.NAO_PUBLICADO,
            alergenos_indisponivel=False,
            filtro_marcador_desativado=False,
            categorias=[],
        )
