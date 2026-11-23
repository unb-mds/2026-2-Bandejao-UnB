"""PrevisaoService: previsão de pico por faixa de horário (RF13, RN06, ADR 0010,
Fila N4 4c).

Calculada sob demanda, em seis passos separados, cada um numa classe:
janela, faixas, contagem, suficiência, média e nível. Todos os números vêm
de `ParametrosFilaConfig` e `HorariosRefeicaoConfig` (Anexo A). O nível sai
só dos check-ins; as respostas à pergunta de saída não entram (ADR 0010).
O passo 7 do N4 (espera estimada) é da BE-E1.
"""

from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum

from apps.cardapio.models import Campus
from apps.fila.checkin_repository import CheckinRepository
from apps.fila.classificador_nivel_fila import ClassificadorNivelFila, NivelFila
from apps.fila.faixa_horario_generator import FaixaHorarioGenerator
from apps.fila.janela_historico_resolver import JanelaHistoricoResolver
from apps.fila.media_por_faixa_calculator import MediaPorFaixaCalculator
from apps.fila.suficiencia_dados_validator import SuficienciaDadosValidator


class StatusPrevisao(StrEnum):
    DISPONIVEL = "disponivel"
    DADOS_INSUFICIENTES = "dados_insuficientes"


@dataclass(frozen=True)
class FaixaPrevista:
    inicio: time
    fim: time
    nivel: NivelFila
    eh_pico: bool


@dataclass(frozen=True)
class PrevisaoPico:
    campus: Campus
    tipo_refeicao: str
    data: date
    status: StatusPrevisao
    faixas: list[FaixaPrevista]


class PrevisaoService:
    def __init__(self):
        self.janela = JanelaHistoricoResolver()
        self.gerador_de_faixas = FaixaHorarioGenerator()
        self.repositorio = CheckinRepository()
        self.suficiencia = SuficienciaDadosValidator()
        self.medias = MediaPorFaixaCalculator()
        self.classificador = ClassificadorNivelFila()

    def calcular(
        self, campus: Campus, tipo_refeicao: str, data: date, hoje: date
    ) -> PrevisaoPico:
        """Os seis passos do N4, na ordem. `hoje` é o dia corrente em Brasília,
        calculado uma vez na view, como o `agora` do check-in.

        Com menos de 3 dias com dados, sai `DADOS_INSUFICIENTES` e nenhuma
        faixa, sem valor de reserva (RF13). A faixa mais cheia é o pico; no
        empate, todas as que têm a maior média são longas e são pico (RN06,
        decisão do grupo). As médias são frações exatas, então o empate é
        igualdade de verdade.
        """
        datas = self.janela.datas_da_janela(data, hoje)
        faixas = self.gerador_de_faixas.faixas(tipo_refeicao)
        contagens = self.repositorio.contar_por_faixa(
            campus, tipo_refeicao, datas, faixas
        )
        if not self.suficiencia.suficiente(contagens):
            return PrevisaoPico(
                campus=campus,
                tipo_refeicao=tipo_refeicao,
                data=data,
                status=StatusPrevisao.DADOS_INSUFICIENTES,
                faixas=[],
            )
        medias = self.medias.calcular(contagens)
        maxima = max(medias)
        return PrevisaoPico(
            campus=campus,
            tipo_refeicao=tipo_refeicao,
            data=data,
            status=StatusPrevisao.DISPONIVEL,
            faixas=[
                FaixaPrevista(
                    inicio=faixa.inicio,
                    fim=faixa.fim,
                    nivel=self.classificador.classificar(media, maxima),
                    eh_pico=media == maxima,
                )
                for faixa, media in zip(faixas, medias, strict=True)
            ],
        )
