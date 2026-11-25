"""Avalia o resultado do Locust contra a meta do RNF01 (BD-14, #184).

Lê o `<prefixo>_stats.csv` do Locust e confere, em cada endpoint do
`cenario`, o p95 (≤ 3 s) e a taxa de falhas (≤ 1%: respostas com erro são
rápidas e mascarariam um p95 ruim). Imprime um resumo em Markdown e sai com
0 (aprovado) ou 1 (reprovado).

    python -m carga.avaliar resultado/carga_stats.csv [--informativo]

Com `--informativo`, que o workflow carga.yml usa em todas as rodadas, o
desempenho não derruba o job: o veredito do RNF01 fica no resumo e no
documento. Mas uma carga que não mediu (um endpoint sem requisição, ou mais
da metade com falha, como numa task quebrada no locustfile) sai com 1 mesmo
assim: isso não é desempenho ruim, é teste quebrado.

A variável USUARIOS, se existir, entra no título do resumo.
"""

import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from carga.cenario import NOME_CARDAPIO, NOME_PREVISAO

META_P95_MS = 3000
LIMITE_FALHAS = 0.01
# Acima disso, a carga não mediu o servidor: o teste está quebrado.
LIMITE_FALHAS_EXECUCAO = 0.5
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
    # Motivos que mostram que a carga não mediu (e não que o servidor é lento).
    problemas_de_execucao: list[str] = field(default_factory=list)

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
            motivo = f"{nome}: nenhuma requisição medida"
            resultado.motivos.append(motivo)
            resultado.problemas_de_execucao.append(motivo)
            continue
        if linha.p95_ms is None:
            resultado.motivos.append(f"{nome}: p95 sem medida")
        elif linha.p95_ms > META_P95_MS:
            resultado.motivos.append(
                f"{nome}: p95 de {linha.p95_ms:.0f} ms, acima de {META_P95_MS} ms"
            )
        if linha.taxa_de_falhas > LIMITE_FALHAS:
            motivo = (
                f"{nome}: {linha.taxa_de_falhas:.1%} de falha "
                f"({linha.falhas} de {linha.requisicoes})"
            )
            resultado.motivos.append(motivo)
            if linha.taxa_de_falhas > LIMITE_FALHAS_EXECUCAO:
                resultado.problemas_de_execucao.append(motivo)
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
        "**Aprovado:** p95 e falhas dentro da meta do RNF01 nos dois endpoints."
        if resultado.aprovado
        else "**Reprovado:**\n" + "\n".join(f"- {m}" for m in resultado.motivos)
    )
    return "\n".join([*linhas, "", veredito, ""])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    informativo = "--informativo" in argv
    arquivos = [a for a in argv if not a.startswith("--")]
    resultado = avaliar(ler_estatisticas(arquivos[0]))
    usuarios = os.environ.get("USUARIOS")
    if usuarios:
        print(f"### {usuarios} usuários simultâneos\n")
    print(markdown(resultado))
    if resultado.problemas_de_execucao:
        print(
            "**A carga não mediu o servidor** (teste quebrado, e não desempenho "
            "ruim): o job falha.\n"
        )
        return 1
    if informativo:
        print(
            "_Informativo no CI: o job não falha por desempenho; o veredito "
            "acima vale para esta rodada._\n"
        )
        return 0
    return 0 if resultado.aprovado else 1


if __name__ == "__main__":
    sys.exit(main())
