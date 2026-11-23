"""Avalia o resultado do Locust contra a meta do RNF01 (BD-14, #184).

Lê o `<prefixo>_stats.csv` do Locust e confere, em cada endpoint do
`cenario`, o p95 (≤ 3 s) e a taxa de falhas (≤ 1%: respostas com erro são
rápidas e mascarariam um p95 ruim). Imprime um resumo em Markdown e sai com
0 (aprovado) ou 1 (reprovado).

    python -m carga.avaliar resultado/carga_stats.csv
"""

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

from carga.cenario import NOME_CARDAPIO, NOME_PREVISAO

META_P95_MS = 3000
LIMITE_FALHAS = 0.01
ENDPOINTS = (NOME_CARDAPIO, NOME_PREVISAO)
AGREGADO = "Aggregated"


@dataclass(frozen=True)
class Linha:
    nome: str
    requisicoes: int
    falhas: int
    p95_ms: float | None
    rps: float

    @property
    def taxa_de_falhas(self) -> float:
        return self.falhas / self.requisicoes if self.requisicoes else 0.0


@dataclass
class Resultado:
    linhas: dict[str, Linha]
    motivos: list[str] = field(default_factory=list)

    @property
    def aprovado(self) -> bool:
        return not self.motivos


def _numero(valor: str) -> float | None:
    valor = (valor or "").strip()
    if not valor or valor == "N/A":
        return None
    return float(valor)


def ler_estatisticas(caminho) -> dict[str, Linha]:
    linhas = {}
    with Path(caminho).open(encoding="utf-8", newline="") as arquivo:
        for registro in csv.DictReader(arquivo):
            nome = registro["Name"]
            linhas[nome] = Linha(
                nome=nome,
                requisicoes=int(registro["Request Count"]),
                falhas=int(registro["Failure Count"]),
                p95_ms=_numero(registro["95%"]),
                rps=_numero(registro["Requests/s"]) or 0.0,
            )
    return linhas


def avaliar(linhas: dict[str, Linha]) -> Resultado:
    resultado = Resultado(linhas=linhas)
    for nome in ENDPOINTS:
        linha = linhas.get(nome)
        if linha is None or not linha.requisicoes:
            resultado.motivos.append(f"{nome}: nenhuma requisição medida")
            continue
        if linha.p95_ms is None or linha.p95_ms > META_P95_MS:
            resultado.motivos.append(
                f"{nome}: p95 de {linha.p95_ms} ms, acima de {META_P95_MS} ms"
            )
        if linha.taxa_de_falhas > LIMITE_FALHAS:
            resultado.motivos.append(
                f"{nome}: {linha.taxa_de_falhas:.1%} de falha "
                f"({linha.falhas} de {linha.requisicoes})"
            )
    return resultado


def _formatar(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.0f}"


def markdown(resultado: Resultado) -> str:
    linhas = [
        "| Endpoint | Requisições | Falhas | Req/s | p95 (ms) | Meta (ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for nome in (*ENDPOINTS, AGREGADO):
        linha = resultado.linhas.get(nome)
        if linha is None:
            linhas.append(f"| {nome} | — | — | — | — | {META_P95_MS} |")
            continue
        linhas.append(
            f"| {nome} | {linha.requisicoes} | {linha.falhas} | "
            f"{linha.rps:.1f} | {_formatar(linha.p95_ms)} | {META_P95_MS} |"
        )
    veredito = (
        "**Aprovado:** p95 dentro da meta do RNF01 nos dois endpoints."
        if resultado.aprovado
        else "**Reprovado:**\n" + "\n".join(f"- {m}" for m in resultado.motivos)
    )
    return "\n".join([*linhas, "", veredito, ""])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    resultado = avaliar(ler_estatisticas(argv[0]))
    print(markdown(resultado))
    return 0 if resultado.aprovado else 1


if __name__ == "__main__":
    sys.exit(main())
