"""Seleção dos alvos e escore da mutação no CI (BE-19, #186, ADR 0013).

O `mutmut` 3.x não tem um modo "só o que mudou no PR": a opção
`use_git_change_detection` só invalida o cache local. O que funciona é passar
ao `mutmut run` o nome dos mutantes com curinga, e o nome de cada mutante
começa pelo módulo em notação de ponto:

    apps/gamificacao/patente_resolver.py  ->  "apps.gamificacao.patente_resolver.*"

Comandos (rodar de dentro de `backend/`):

    python scripts/mutacao_incremental.py alvos origin/develop
        Imprime um curinga por linha para o que o PR mudou em relação à base.
        Sem saída quando o PR não mexe em módulo crítico nem na configuração
        da mutação. Saída 2 se o `git diff` falhar.

    python scripts/mutacao_incremental.py modulo cardapio
        Imprime os curingas de um módulo crítico inteiro (rodada semanal).

    python scripts/mutacao_incremental.py escore --minimo 50 [rótulo=caminho ...]
        Calcula o escore a partir do `mutmut-cicd-stats.json` (padrão:
        `mutants/mutmut-cicd-stats.json`). Com um arquivo (o PR), o mínimo vale
        para o conjunto dos mutantes rodados; com vários (a rodada semanal),
        vale para cada um. Saída 0: no mínimo. Saída 1: abaixo do mínimo.
        Saída 2: não dá para medir (JSON ausente, ilegível ou sem os campos do
        mutmut, nenhum mutante avaliado ou rodada interrompida).

    python scripts/mutacao_incremental.py conferir alvos.txt resultados.txt
        Confere os curingas contra a saída de `mutmut results --all true`:
        avisa (`::warning::`) o curinga que não casou com nenhum mutante e sai
        com 2 se o formato dos nomes dos mutantes mudou.

Só usa a biblioteca padrão: roda antes de qualquer `pip install`.
"""

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import dataclass, fields
from pathlib import Path, PurePosixPath

# Apps dos módulos críticos (Plano de Testes, seção 2). Tem que bater com o
# `only_mutate` do setup.cfg (há teste para isso).
APPS_CRITICOS = ("cadastro", "cardapio", "avaliacao", "fila", "gamificacao")

# Arquivos que não geram curinga. Os quatro primeiros e as migrations são os
# de `do_not_mutate` no setup.cfg. O `__init__.py` fica fora porque o nome dos
# mutantes de um `__init__.py` é o do pacote (`apps.fila.x_...`), então o
# curinga dele seria o app inteiro; e os dos apps críticos não têm código (há
# teste para isso).
ARQUIVOS_FORA = ("admin.py", "apps.py", "urls.py", "__init__.py")
PASTAS_FORA = ("migrations",)

# Módulos da rodada semanal: um job da matriz para cada (há teste que compara
# com o YAML).
MODULOS = (
    "cadastro",
    "cardapio/leitor",
    "cardapio",
    "avaliacao",
    "fila",
    "gamificacao",
)

# Mudanças que alteram como a mutação roda, sem tocar em módulo crítico. Um
# PR que mexe nelas roda a mutação num alvo fixo, pequeno e conhecido, para a
# configuração nova ser exercitada antes do merge. Caminhos a partir de
# `backend/`, exceto o workflow.
CONFIGURACAO_DA_MUTACAO = (
    "setup.cfg",
    "conftest.py",
    "pytest.ini",
    "requirements-dev.txt",
    "scripts/mutacao_incremental.py",
    "config/",
    "../.github/workflows/backend-ci.yml",
)
ALVO_DA_CONFIGURACAO = "apps.gamificacao.patente_resolver.*"

STATS_PADRAO = "mutants/mutmut-cicd-stats.json"


# --- Arquivos alterados -> curingas ------------------------------------------


def _relativo_ao_backend(caminho: str) -> PurePosixPath:
    """Caminho a partir de `backend/`; o que está fora começa com `..`."""
    partes = PurePosixPath(caminho.replace("\\", "/")).parts
    if partes and partes[0] == "backend":
        return PurePosixPath(*partes[1:]) if len(partes) > 1 else PurePosixPath(".")
    if partes and partes[0] in ("apps", "config", "scripts", "tests"):
        # Já relativo ao backend (é como os testes chamam).
        return PurePosixPath(*partes)
    if len(partes) == 1 and caminho in CONFIGURACAO_DA_MUTACAO:
        return PurePosixPath(caminho)
    return PurePosixPath("..", *partes)


def _e_configuracao(caminho: PurePosixPath) -> bool:
    texto = caminho.as_posix()
    return any(
        texto.startswith(gatilho) if gatilho.endswith("/") else texto == gatilho
        for gatilho in CONFIGURACAO_DA_MUTACAO
    )


def _curinga(caminho: PurePosixPath) -> str:
    """apps/fila/x.py -> apps.fila.x.*"""
    return ".".join(caminho.with_suffix("").parts) + ".*"


def _mutavel(caminho: PurePosixPath) -> bool:
    return caminho.name not in ARQUIVOS_FORA and not any(
        p in PASTAS_FORA for p in caminho.parts
    )


def _curingas_do_teste(caminho: PurePosixPath, raiz: Path) -> list[str]:
    """Curingas do código que um arquivo de `apps/<app>/tests/` cobre.

    - `test_<nome>.py` -> `apps/<app>/<nome>.py`, ou `<nome>.py` num subpacote
      do app (por exemplo o leitor), se existir;
    - no cardápio, o que tem `leitor` no nome (`test_leitor_*.py`,
      `apoio_leitor.py`) -> o leitor inteiro, e o resto -> o cardápio sem o
      leitor (o leitor tem quase metade dos mutantes da base);
    - nos outros apps, o resto (teste de endpoint, apoio, conftest) -> o app
      inteiro.
    """
    app = caminho.parts[1]
    nome = caminho.stem.removeprefix("test_")

    if caminho.stem.startswith("test_"):
        pasta_do_app = raiz / "apps" / app
        candidatos = [pasta_do_app / f"{nome}.py"]
        candidatos += sorted(
            sub / f"{nome}.py"
            for sub in pasta_do_app.iterdir()
            if sub.is_dir() and sub.name not in ("tests", *PASTAS_FORA)
        )
        for candidato in candidatos:
            if candidato.is_file():
                return [_curinga(PurePosixPath(candidato.relative_to(raiz).as_posix()))]

    if app == "cardapio":
        if "leitor" in nome:
            return ["apps.cardapio.leitor.*"]
        return curingas_do_modulo("cardapio", raiz)
    return [f"apps.{app}.*"]


def curingas(alterados: list[str], raiz: Path) -> list[str]:
    """Curingas do `mutmut run` para os arquivos alterados no PR.

    `alterados` vem do `git diff --name-only` (a partir da raiz do
    repositório; caminhos a partir de `backend/` também valem) e `raiz` é a
    pasta `backend/`.
    """
    encontrados: set[str] = set()
    for texto in alterados:
        caminho = _relativo_ao_backend(texto)
        if _e_configuracao(caminho):
            encontrados.add(ALVO_DA_CONFIGURACAO)
            continue
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
            # Um teste alterado, ou apagado, muda o escore do código que ele
            # cobre: é o caso do PR de prova.
            encontrados.update(_curingas_do_teste(caminho, raiz))
        elif (raiz / caminho).is_file():
            encontrados.add(_curinga(caminho))
        # Senão, é código apagado no PR: não há mais o que mutar.

    # "apps.fila.*" já casa com "apps.fila.checkin_service.*".
    return sorted(
        c
        for c in encontrados
        if not any(
            o != c and o.endswith(".*") and c.startswith(o[:-1]) for o in encontrados
        )
    )


def arquivos_alterados(base: str, raiz: Path) -> list[str]:
    """Arquivos alterados entre a base e o HEAD, a partir da raiz do repositório.

    Os três pontos comparam com o ponto em que o PR saiu da base: o que mudou
    só na base não conta. Precisa do histórico (`fetch-depth: 0` no checkout).
    """
    saida = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
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


class JsonInvalido(ValueError):
    """O `mutmut-cicd-stats.json` não tem a forma que o mutmut 3.8.1 grava."""


@dataclass(frozen=True)
class Escore:
    killed: int
    timeout: int
    survived: int
    no_tests: int
    suspicious: int
    segfault: int
    check_was_interrupted_by_user: int = 0

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
                getattr(self, campo.name) + getattr(outro, campo.name)
                for campo in fields(self)
            )
        )


# Sem estes, o JSON não é do mutmut (ou um upgrade renomeou os campos). Os
# outros podem faltar e contam como zero.
CAMPOS_OBRIGATORIOS = ("killed", "survived")


def calcular_escore(stats: object) -> Escore:
    """Escore a partir do `mutmut-cicd-stats.json`.

    - `timeout` conta como morto: o mutante travou o código, e a suíte
      percebeu;
    - `no_tests` (nenhum teste passa pela linha), `suspicious` e `segfault`
      contam contra;
    - `skipped` e os não rodados ficam fora. O `total` do JSON não serve:
      ele conta todos os mutantes gerados, inclusive os que não rodaram no
      modo incremental.

    Levanta `JsonInvalido` se o JSON não for um objeto com os campos do mutmut
    em números inteiros não negativos.
    """
    if not isinstance(stats, dict):
        raise JsonInvalido("o JSON não é um objeto")
    faltando = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in stats]
    if faltando:
        raise JsonInvalido(f"faltam os campos {', '.join(faltando)}")
    valores = []
    for campo in fields(Escore):
        valor = stats.get(campo.name, 0)
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
            raise JsonInvalido(
                f"o campo {campo.name} não é um inteiro não negativo: {valor!r}"
            )
        valores.append(valor)
    return Escore(*valores)


def _porcento(e: Escore) -> str:
    if not e.avaliados:
        return "sem mutantes"
    # Duas casas, truncadas e em conta inteira: 49,999% não pode aparecer como
    # "50,00% ABAIXO".
    centesimos = e.mortos * 10000 // e.avaliados
    return f"{centesimos // 100},{centesimos % 100:02d}%"


def _linha_da_tabela(rotulo: str, e: Escore) -> str:
    return (
        f"| {rotulo} | {e.killed} | {e.timeout} | {e.survived} | {e.no_tests} "
        f"| {e.suspicious} | {e.segfault} | {e.avaliados} | {_porcento(e)} |"
    )


def _comando_escore(args: argparse.Namespace) -> int:
    pares = args.arquivos or [f"PR={STATS_PADRAO}"]
    escores: list[tuple[str, Escore]] = []
    for par in pares:
        rotulo, _, caminho = par.rpartition("=")
        rotulo = rotulo or Path(caminho).parent.name or caminho
        try:
            escore = calcular_escore(
                json.loads(Path(caminho).read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as erro:
            # Sem o JSON, o mutmut não terminou: não pode virar verde, nem se
            # confundir com "abaixo do mínimo".
            print(
                f"Erro: não consegui ler {caminho} ({rotulo}): {erro}", file=sys.stderr
            )
            return 2
        if escore.check_was_interrupted_by_user:
            print(
                f"Erro: a rodada de {rotulo} foi interrompida "
                f"({escore.check_was_interrupted_by_user} mutantes); o escore seria de uma "
                "amostra.",
                file=sys.stderr,
            )
            return 2
        if not escore.avaliados:
            # O "nada a testar" é decidido antes, no job: este passo só roda
            # depois que o mutmut testou mutantes.
            print(
                f"Erro: nenhum mutante avaliado em {rotulo} ({caminho}).",
                file=sys.stderr,
            )
            return 2
        escores.append((rotulo, escore))

    abaixo = []
    for rotulo, e in escores:
        situacao = ""
        if e.mortos * 100 < args.minimo * e.avaliados:
            abaixo.append(rotulo)
            situacao = f" ABAIXO DE {args.minimo:g}%"
        print(
            f"Mutação {rotulo}: {e.mortos} mortos (com {e.timeout} por tempo) de "
            f"{e.avaliados} avaliados ({e.survived} sobreviventes, {e.no_tests} sem "
            f"testes, {e.suspicious} suspeitos, {e.segfault} segfault): "
            f"{_porcento(e)}{situacao}"
        )
    geral = escores[0][1]
    for _, e in escores[1:]:
        geral = geral + e
    if len(escores) > 1:
        print(f"Mutação geral: {geral.mortos} de {geral.avaliados}: {_porcento(geral)}")

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        if len(escores) > 1:
            regra = f"Mínimo: {args.minimo:g}% em cada módulo (RNF06, ADR 0013)."
        else:
            regra = (
                f"Mínimo: {args.minimo:g}% no conjunto dos mutantes dos arquivos alterados "
                "(RNF06, ADR 0013)."
            )
        linhas = [
            "## Escore de mutação",
            "",
            regra,
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


# --- Conferência dos curingas -------------------------------------------------


def _comando_conferir(args: argparse.Namespace) -> int:
    alvos = [
        linha.strip()
        for linha in Path(args.alvos).read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    # Linhas de `mutmut results --all true`: "    <nome>: <situação>".
    nomes = [
        linha.strip().rsplit(": ", 1)[0]
        for linha in Path(args.resultados).read_text(encoding="utf-8").splitlines()
        if ": " in linha
    ]
    if not any(nome.startswith("apps.") for nome in nomes):
        print(
            "::error::Nenhum mutante com nome em apps.*: o formato dos nomes dos "
            "mutantes mudou (upgrade do mutmut ou source_paths) ou nenhum mutante "
            "foi gerado. Os curingas do job não casariam com nada."
        )
        return 2
    for alvo in alvos:
        quantos = sum(1 for nome in nomes if fnmatch.fnmatchcase(nome, alvo))
        if quantos:
            print(f"{alvo}: {quantos} mutantes")
        else:
            print(
                f"::warning::{alvo} não casou com nenhum mutante (arquivo sem nada que "
                "o mutmut saiba mutar, ou curinga errado)."
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    alvos = sub.add_parser("alvos", help="curingas do que o PR mudou")
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

    conferir = sub.add_parser(
        "conferir", help="confere os curingas contra os mutantes gerados"
    )
    conferir.add_argument("alvos", help="arquivo com um curinga por linha")
    conferir.add_argument("resultados", help="saída de `mutmut results --all true`")

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
    if args.comando == "conferir":
        return _comando_conferir(args)
    return _comando_escore(args)


if __name__ == "__main__":
    sys.exit(main())
