"""HorarioRefeicaoResolver: a refeição padrão da RN05 (Release 2, Exposição N4 4a).

Analogia: é o relógio da entrada do RU com a lista do dia ao lado. Quem
chega pergunta "o que tem agora?"; ele responde com a refeição em andamento,
senão a próxima, senão a última (já encerrada). Só que este relógio não
tem ponteiro próprio: a hora vem de fora (`agora`), calculada uma vez na
view, para os testes poderem simular qualquer horário.

Os horários vêm do `HorariosRefeicaoConfig` (Anexo A), lidos a cada chamada.
As refeições que existem no dia vêm do PDF (RF06.2), pela lista recebida.
"""

from dataclasses import dataclass
from datetime import date, datetime, time

from django.utils import timezone

from apps.cardapio.models import Refeicao, TipoRefeicao
from config.parametros import HorariosRefeicaoConfig

# Ordem do dia, a mesma do Anexo A.
ORDEM_DO_DIA = (TipoRefeicao.CAFE, TipoRefeicao.ALMOCO, TipoRefeicao.JANTAR)


@dataclass(frozen=True)
class RefeicaoPadrao:
    refeicao: str
    dia: date
    encerrada: bool


def intervalo(tipo: str) -> tuple[time, time]:
    """Início e fim da refeição no Anexo A, lidos agora da configuração."""
    return {
        TipoRefeicao.CAFE: HorariosRefeicaoConfig.horario_cafe,
        TipoRefeicao.ALMOCO: HorariosRefeicaoConfig.horario_almoco,
        TipoRefeicao.JANTAR: HorariosRefeicaoConfig.horario_jantar,
    }[tipo]


def _hora_local(agora: datetime) -> time:
    return timezone.localtime(agora).time()


def _em_andamento(hora: time, tipo: str) -> bool:
    # Início e fim incluídos: a mesma comparação do JanelaCheckinValidator
    # (apps/fila), para o check-in e o cardápio nunca discordarem.
    inicio, fim = intervalo(tipo)
    return inicio <= hora <= fim


def _tipos_na_ordem(refeicoes_do_dia: list[Refeicao]) -> list[str]:
    tipos = {refeicao.tipo for refeicao in refeicoes_do_dia}
    return [tipo for tipo in ORDEM_DO_DIA if tipo in tipos]


class HorarioRefeicaoResolver:
    def refeicao_padrao(
        self, agora: datetime, refeicoes_do_dia: list[Refeicao]
    ) -> RefeicaoPadrao:
        """Refeição padrão entre as refeições de um dia (RN05, itens 1 a 4).

        Para o dia de hoje: (1) a em andamento; (2) senão, a próxima; (3)
        senão, a última do dia, encerrada (até as 23h59, porque à meia-noite
        o "hoje" já é outro dia: item 4). Para um dia futuro, a primeira; para
        um dia passado, a última, encerrada.

        O item 5 (dia sem serviço) fica com o CardapioQueryService: a lista
        vazia é um erro de quem chamou.
        """
        if not refeicoes_do_dia:
            raise ValueError("refeicao_padrao precisa de ao menos uma refeição.")
        dia = refeicoes_do_dia[0].data
        hoje = timezone.localtime(agora).date()
        tipos = _tipos_na_ordem(refeicoes_do_dia)
        if dia > hoje:
            return RefeicaoPadrao(refeicao=tipos[0], dia=dia, encerrada=False)
        if dia < hoje:
            return RefeicaoPadrao(refeicao=tipos[-1], dia=dia, encerrada=True)
        tipo = self.refeicao_em_andamento(agora, refeicoes_do_dia) or (
            self.proxima_refeicao(agora, refeicoes_do_dia)
        )
        if tipo is not None:
            return RefeicaoPadrao(refeicao=tipo, dia=dia, encerrada=False)
        return RefeicaoPadrao(
            refeicao=self.ultima_refeicao_do_dia(refeicoes_do_dia),
            dia=dia,
            encerrada=True,
        )

    def refeicao_em_andamento(
        self, agora: datetime, refeicoes_do_dia: list[Refeicao]
    ) -> str | None:
        """A refeição do PDF cujo horário contém `agora`, ou None."""
        hora = _hora_local(agora)
        for tipo in _tipos_na_ordem(refeicoes_do_dia):
            if _em_andamento(hora, tipo):
                return tipo
        return None

    def proxima_refeicao(
        self, agora: datetime, refeicoes_do_dia: list[Refeicao]
    ) -> str | None:
        """A primeira refeição do PDF que ainda não começou, ou None."""
        hora = _hora_local(agora)
        for tipo in _tipos_na_ordem(refeicoes_do_dia):
            if hora < intervalo(tipo)[0]:
                return tipo
        return None

    def ultima_refeicao_do_dia(self, refeicoes_do_dia: list[Refeicao]) -> str:
        """A última refeição do dia na ordem do Anexo A."""
        return _tipos_na_ordem(refeicoes_do_dia)[-1]
