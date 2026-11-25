"""RankingService: o ranking semestral de um campus, calculado na consulta
(RF27.2, RN12, Gamificação N4 4c).

Nada é gravado: quem desliga a adesão ou tem a conta suspensa sai do ranking
na próxima consulta.
"""

from datetime import date

from django.contrib.auth import get_user_model

from apps.cardapio.models import Campus
from apps.gamificacao.pontuacao_repository import PontuacaoRepository
from apps.gamificacao.ranking import LinhaRanking
from apps.gamificacao.semestre_resolver import SemestreResolver
from config.parametros import ParametrosGamificacaoConfig


class RankingService:
    def __init__(
        self, semestres: SemestreResolver | None = None, tamanho: int | None = None
    ):
        """Sem argumentos, usa o `SemestreResolver` e o tamanho do ranking da
        `ParametrosGamificacaoConfig`. Os testes passam os próprios."""
        self.semestres = semestres or SemestreResolver()
        self.tamanho = (
            ParametrosGamificacaoConfig.tamanho_ranking if tamanho is None else tamanho
        )
        self.pontuacoes = PontuacaoRepository()

    def semestre_corrente(self, hoje: date) -> str:
        return self.semestres.semestre_de(hoje)

    def top_publico(self, campus: Campus, semestre: str) -> list[LinhaRanking]:
        """Os `tamanho` primeiros elegíveis, com posição de 1 em diante.

        O corte fica no banco (`LIMIT`), para o MySQL parar de ler o índice
        do ranking quando achar as linhas (BD-10). As contas vêm numa segunda
        consulta, pelos ids e com a pontuação junto, e não por
        `select_related` na primeira, que faria o MySQL ordenar em arquivo
        temporário. Uma conta excluída entre as duas consultas fica de fora,
        e as posições seguem sem buraco.
        """
        linhas = list(self.pontuacoes.elegiveis(campus, semestre)[: self.tamanho])
        contas = (
            get_user_model()
            .objects.select_related("pontuacao")
            .in_bulk([linha.usuario_id for linha in linhas])
        )
        presentes = [linha for linha in linhas if linha.usuario_id in contas]
        return [
            LinhaRanking(
                conta=contas[linha.usuario_id], posicao=posicao, pontos=linha.pontos
            )
            for posicao, linha in enumerate(presentes, start=1)
        ]
