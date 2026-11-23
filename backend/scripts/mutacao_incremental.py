"""Seleção dos alvos e escore da mutação no CI (BE-19, #186, ADR 0013).

O `mutmut` 3.x não tem um modo "só o que mudou no PR": a opção
`use_git_change_detection` só invalida o cache local. O que funciona é passar
ao `mutmut run` o nome dos mutantes com curinga, e o nome de cada mutante
começa pelo módulo em notação de ponto:

    apps/gamificacao/patente_resolver.py  ->  "apps.gamificacao.patente_resolver.*"

Comandos (rodar de dentro de `backend/`):

    python scripts/mutacao_incremental.py alvos origin/develop
        Imprime um curinga por linha para os arquivos críticos alterados no PR
        em relação à base. Sem saída quando o PR não toca em módulo crítico.

    python scripts/mutacao_incremental.py modulo cardapio
        Imprime os curingas de um módulo crítico inteiro (rodada semanal).

    python scripts/mutacao_incremental.py escore --minimo 50 [rótulo=caminho ...]
        Calcula o escore a partir do `mutmut-cicd-stats.json` (padrão:
        `mutants/mutmut-cicd-stats.json`) e sai com 1 abaixo do mínimo. Com
        vários arquivos, a meta vale para cada um (cada módulo crítico).

Só usa a biblioteca padrão: roda antes de qualquer `pip install`.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Apps dos módulos críticos (Plano de Testes, seção 2). Tem que bater com o
# `only_mutate` do setup.cfg (há teste para isso).
APPS_CRITICOS = ("cadastro", "cardapio", "avaliacao", "fila", "gamificacao")

# Os mesmos de `do_not_mutate` no setup.cfg, mais os `__init__.py`.
ARQUIVOS_FORA = ("admin.py", "apps.py", "urls.py", "__init__.py")
PASTAS_FORA = ("migrations",)

# Módulos da rodada semanal: um job da matriz para cada.
MODULOS = (
    "cadastro",
    "cardapio/leitor",
    "cardapio",
    "avaliacao",
    "fila",
    "gamificacao",
)

STATS_PADRAO = "mutants/mutmut-cicd-stats.json"


# --- Arquivos alterados -> curingas ------------------------------------------


def _relativo_ao_backend(caminho: str) -> PurePosixPath:
    partes = PurePosixPath(caminho.replace("\\", "/")).parts
    if partes and partes[0] == "backend":
        partes = partes[1:]
    return PurePosixPath(*partes) if partes else PurePosixPath(".")


def _curinga(caminho: PurePosixPath) -> str:
    """apps/fila/x.py -> apps.fila.x.*"""
    return ".".join(caminho.with_suffix("").parts) + ".*"


def _mutavel(caminho: PurePosixPath) -> bool:
    return caminho.name not in ARQUIVOS_FORA and not any(
        p in PASTAS_FORA for p in caminho.parts
    )


def _modulo_do_teste(caminho: PurePosixPath, raiz: Path) -> str:
    """Curinga do código que um arquivo de `apps/<app>/tests/` cobre.

    - `test_leitor_*.py` -> o leitor inteiro;
    - `test_<nome>.py` -> `apps/<app>/<nome>.py`, ou `<nome>.py` num subpacote
      do app (por exemplo o leitor), se existir;
    - senão (teste de endpoint, apoio, conftest), o app inteiro.
    """
    app = caminho.parts[1]
    app_inteiro = f"apps.{app}.*"
    nome = caminho.stem
    if not nome.startswith("test_"):
        return app_inteiro
    nome = nome.removeprefix("test_")
    if app == "cardapio" and nome.startswith("leitor_"):
        return "apps.cardapio.leitor.*"

    pasta_do_app = raiz / "apps" / app
    candidatos = [pasta_do_app / f"{nome}.py"]
    candidatos += sorted(
        sub / f"{nome}.py"
        for sub in pasta_do_app.iterdir()
        if sub.is_dir() and sub.name not in ("tests", *PASTAS_FORA)
    )
    for candidato in candidatos:
        if candidato.is_file():
            return _curinga(PurePosixPath(candidato.relative_to(raiz).as_posix()))
    return app_inteiro


def curingas(alterados: list[str], raiz: Path) -> list[str]:
    """Curingas do `mutmut run` para os arquivos alterados no PR.

    `alterados` vem do `git diff --name-only` (relativo ao backend ou à raiz
    do repositório) e `raiz` é a pasta `backend/`.
    """
    encontrados: set[str] = set()
    for texto in alterados:
        caminho = _relativo_ao_backend(texto)
        partes = caminho.parts
        if (
            len(partes) < 3
            or partes[0] != "apps"
            or partes[1] not in APPS_CRITICOS
            or caminho.suffix != ".py"
            or not _mutavel(caminho)
        ):
            continue
        if "tests" in partes:
            # Um teste alterado (ou apagado) muda o escore do código que ele
            # cobre: é o caso do PR de prova.
            encontrados.add(_modulo_do_teste(caminho, raiz))
        elif (raiz / caminho).is_file():
            # Arquivo apagado no PR: não há mais código a mutar.
            encontrados.add(_curinga(caminho))

    # "apps.cardapio.*" já casa com "apps.cardapio.leitor.x.*".
    return sorted(
        c
        for c in encontrados
        if not any(
            o != c and o.endswith(".*") and c.startswith(o[:-1]) for o in encontrados
        )
    )


def arquivos_alterados(base: str, raiz: Path) -> list[str]:
    """Arquivos de `apps/` alterados entre a base e o HEAD, relativos a `raiz`.

    Os três pontos comparam com o ponto em que o PR saiu da base: o que mudou
    só na base não conta. Precisa do histórico (`fetch-depth: 0` no checkout).
    """
    saida = subprocess.run(
        ["git", "diff", "--name-only", "--relative", f"{base}...HEAD", "--", "apps"],
        cwd=raiz,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [linha for linha in saida.splitlines() if linha]


def curingas_do_modulo(modulo: str, raiz: Path) -> list[str]:
    """Curingas de um módulo crítico inteiro, para a rodada semanal."""
    if modulo not in MODULOS:
        raise ValueError(
            f"Módulo desconhecido: {modulo}. Use um de {', '.join(MODULOS)}."
        )
    if modulo == "cardapio/leitor":
        return ["apps.cardapio.leitor.*"]
    if modulo != "cardapio":
        return [f"apps.{modulo}.*"]
    # "apps.cardapio.*" também casaria com o leitor: lista os arquivos.
    pasta = raiz / "apps" / "cardapio"
    arquivos = []
    for arquivo in sorted(pasta.rglob("*.py")):
        caminho = PurePosixPath(arquivo.relative_to(raiz).as_posix())
        if {"tests", "leitor"} & set(caminho.parts) or not _mutavel(caminho):
            continue
        arquivos.append(_curinga(caminho))
    return arquivos


# --- Escore ------------------------------------------------------------------


@dataclass(frozen=True)
class Escore:
    killed: int
    timeout: int
    survived: int
    no_tests: int
    suspicious: int
    segfault: int

    @property
    def mortos(self) -> int:
        return self.killed + self.timeout

    @property
    def avaliados(self) -> int:
        return (
            self.killed
            + self.timeout
            + self.survived
            + self.no_tests
            + self.suspicious
            + self.segfault
        )

    @property
    def escore(self) -> float | None:
        return self.mortos / self.avaliados if self.avaliados else None

    def __add__(self, outro: "Escore") -> "Escore":
        return Escore(
            *(
                getattr(self, campo) + getattr(outro, campo)
                for campo in self.__dataclass_fields__
            )
        )


def calcular_escore(stats: dict) -> Escore:
    """Escore a partir do `mutmut-cicd-stats.json`.

    - `timeout` conta como morto: o mutante travou o código, e a suíte
      percebeu;
    - `no_tests` (nenhum teste passa pela linha), `suspicious` e `segfault`
      contam contra;
    - `skipped` e os não rodados ficam fora. O `total` do JSON não serve:
      ele conta todos os mutantes gerados, inclusive os que não rodaram no
      modo incremental.
    """
    return Escore(
        *(int(stats.get(campo, 0)) for campo in Escore.__dataclass_fields__),
    )


def _porcento(valor: float | None) -> str:
    if valor is None:
        return "nada a testar"
    return f"{valor * 100:.1f}%".replace(".", ",")


def _linha_da_tabela(rotulo: str, e: Escore) -> str:
    return (
        f"| {rotulo} | {e.killed} | {e.timeout} | {e.survived} | {e.no_tests} "
        f"| {e.suspicious} | {e.segfault} | {e.avaliados} | {_porcento(e.escore)} |"
    )


def _comando_escore(args: argparse.Namespace) -> int:
    pares = args.arquivos or [f"PR={STATS_PADRAO}"]
    escores: list[tuple[str, Escore]] = []
    for par in pares:
        rotulo, _, caminho = par.rpartition("=")
        rotulo = rotulo or Path(caminho).parent.name or caminho
        try:
            dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            # Sem o JSON, o mutmut não terminou: não pode virar verde.
            print(f"Erro: não consegui ler {caminho}: {erro}", file=sys.stderr)
            return 2
        escores.append((rotulo, calcular_escore(dados)))

    minimo = args.minimo / 100
    abaixo = []
    for rotulo, e in escores:
        situacao = ""
        if e.escore is not None and e.escore < minimo:
            abaixo.append(rotulo)
            situacao = f" ABAIXO DE {args.minimo:g}%"
        print(
            f"Mutação {rotulo}: {e.mortos} mortos (com {e.timeout} por tempo) de "
            f"{e.avaliados} avaliados ({e.survived} sobreviventes, {e.no_tests} sem "
            f"testes, {e.suspicious} suspeitos, {e.segfault} segfault): "
            f"{_porcento(e.escore)}{situacao}"
        )
    geral = escores[0][1]
    for _, e in escores[1:]:
        geral = geral + e
    if len(escores) > 1:
        print(
            f"Mutação geral: {geral.mortos} de {geral.avaliados}: {_porcento(geral.escore)}"
        )

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        linhas = [
            "## Escore de mutação",
            "",
            f"Mínimo: {args.minimo:g}% em cada módulo (RNF06, ADR 0013).",
            "",
            (
                "| Alvo | Mortos | Por tempo | Sobreviventes | Sem testes | Suspeitos "
                "| Segfault | Avaliados | Escore |"
            ),
            "|---|---|---|---|---|---|---|---|---|",
            *(_linha_da_tabela(r, e) for r, e in escores),
        ]
        if len(escores) > 1:
            linhas.append(_linha_da_tabela("**Geral**", geral))
        if abaixo:
            linhas += ["", f"**Abaixo do mínimo:** {', '.join(abaixo)}."]
        with open(resumo, "a", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(linhas) + "\n")

    return 1 if abaixo else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    alvos = sub.add_parser(
        "alvos", help="curingas dos arquivos críticos alterados no PR"
    )
    alvos.add_argument("base", help="referência da base, por exemplo origin/develop")

    modulo = sub.add_parser("modulo", help="curingas de um módulo crítico inteiro")
    modulo.add_argument("nome", choices=MODULOS)

    escore = sub.add_parser("escore", help="escore a partir do mutmut-cicd-stats.json")
    escore.add_argument("--minimo", type=float, default=50.0, help="em %% (padrão: 50)")
    escore.add_argument(
        "arquivos",
        nargs="*",
        metavar="rótulo=caminho",
        help=f"um ou mais JSONs (padrão: {STATS_PADRAO})",
    )

    args = parser.parse_args(argv)
    raiz = Path.cwd()
    if args.comando == "alvos":
        try:
            alterados = arquivos_alterados(args.base, raiz)
        except subprocess.CalledProcessError as erro:
            print(f"Erro no git diff: {erro.stderr.strip()}", file=sys.stderr)
            return 2
        for curinga in curingas(alterados, raiz):
            print(curinga)
        return 0
    if args.comando == "modulo":
        for curinga in curingas_do_modulo(args.nome, raiz):
            print(curinga)
        return 0
    return _comando_escore(args)


if __name__ == "__main__":
    sys.exit(main())
