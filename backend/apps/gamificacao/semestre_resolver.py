"""SemestreResolver: o semestre de uma data (RN12, Gamificação N4 4a).

Cada semestre vai do dia seguinte ao término do anterior até o próprio
término, como as estações de uma linha de metrô: entre o término de um e o do
próximo, a data pertence ao próximo. Por isso as férias contam para o
semestre que vem, e depois do último término configurado a data já é do
semestre seguinte, aberto até alguém configurar o término dele.

A BE-17 (ranking) reaproveita esta classe.
"""

from datetime import date

from config.parametros import ParametrosGamificacaoConfig


def semestre_seguinte(rotulo: str) -> str:
    """`"2026.2"` → `"2027.1"`; `"2027.1"` → `"2027.2"`."""
    ano, periodo = (int(parte) for parte in rotulo.split("."))
    return f"{ano}.2" if periodo == 1 else f"{ano + 1}.1"


class SemestreResolver:
    def __init__(
        self, datas: dict[str, date] | None = None, inicial: str | None = None
    ):
        """Sem argumentos, lê a `ParametrosGamificacaoConfig`. Os testes passam
        as datas aqui, para não depender da config global."""
        self.datas = (
            ParametrosGamificacaoConfig.datas_termino_semestre
            if datas is None
            else datas
        )
        self.inicial = (
            ParametrosGamificacaoConfig.semestre_inicial if inicial is None else inicial
        )

    def semestre_de(self, data: date) -> str:
        """O primeiro semestre cujo término é igual ou posterior a `data`.

        Sem nenhuma data configurada, o semestre é o `inicial` (o atual).
        """
        if not self.datas:
            return self.inicial
        por_termino = sorted(self.datas.items(), key=lambda item: item[1])
        for rotulo, termino in por_termino:
            if data <= termino:
                return rotulo
        ultimo, _ = por_termino[-1]
        return semestre_seguinte(ultimo)
