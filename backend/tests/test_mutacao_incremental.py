"""Seleção e escore da mutação no CI (BE-19, #186).

ADR 0013, decisão 6, e Plano de Testes, seções 3.7 e 5.1: nos PRs, o job
`mutacao` roda o `mutmut` só nos arquivos críticos alterados e falha abaixo
de 50%; toda semana, a base inteira roda, módulo a módulo.

O `mutmut` 3.x não tem um modo "só o que mudou", então o script
`scripts/mutacao_incremental.py` converte os arquivos alterados no PR em
curingas do nome dos mutantes (`apps/fila/x.py` -> `apps.fila.x.*`) e
calcula o escore a partir do `mutants/mutmut-cicd-stats.json`.

Estes testes rodam no job `testes`, e não dentro da mutação (que só roda os
testes de `apps/`, ver o `setup.cfg`).
"""

import configparser
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ_BACKEND / "scripts" / "mutacao_incremental.py"
SETUP_CFG = RAIZ_BACKEND / "setup.cfg"


def carregar_script():
    spec = importlib.util.spec_from_file_location("mutacao_incremental", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def mi():
    return carregar_script()


def criar(raiz: Path, *caminhos: str) -> None:
    """Cria arquivos vazios dentro de `raiz` (o backend de mentira)."""
    for caminho in caminhos:
        arquivo = raiz / caminho
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text("", encoding="utf-8")


@pytest.fixture
def backend(tmp_path):
    """Um backend de mentira com a forma dos apps de verdade."""
    criar(
        tmp_path,
        "apps/gamificacao/patente_resolver.py",
        "apps/gamificacao/pontuacao_service.py",
        "apps/gamificacao/tests/test_patente_resolver.py",
        "apps/gamificacao/tests/test_pontuacao_endpoints.py",
        "apps/cardapio/filtro_dieta_service.py",
        "apps/cardapio/leitor/cardapio_downloader.py",
        "apps/cardapio/leitor/cardapio_pdf_parser.py",
        "apps/cardapio/tests/test_cardapio_downloader.py",
        "apps/cardapio/tests/test_leitor_pdf.py",
        "apps/cardapio/tests/test_filtro_dieta_service.py",
        "apps/cardapio/tests/apoio_leitor.py",
        "apps/fila/checkin_service.py",
        "apps/fila/management/commands/desvincular_registros_fila.py",
        "apps/fila/migrations/0001_initial.py",
        "apps/fila/admin.py",
        "apps/fila/apps.py",
        "apps/fila/urls.py",
        "apps/fila/__init__.py",
        "config/settings.py",
    )
    return tmp_path


# --- Arquivos alterados -> curingas -----------------------------------------


def test_arquivo_critico_vira_curinga_do_modulo(mi, backend):
    assert mi.curingas(["apps/gamificacao/patente_resolver.py"], backend) == [
        "apps.gamificacao.patente_resolver.*"
    ]


def test_caminho_a_partir_da_raiz_do_repositorio_tambem_vale(mi, backend):
    assert mi.curingas(["backend/apps/fila/checkin_service.py"], backend) == [
        "apps.fila.checkin_service.*"
    ]


def test_arquivo_do_leitor_vira_curinga_com_o_subpacote(mi, backend):
    assert mi.curingas(["apps/cardapio/leitor/cardapio_pdf_parser.py"], backend) == [
        "apps.cardapio.leitor.cardapio_pdf_parser.*"
    ]


def test_comando_de_management_e_critico(mi, backend):
    caminho = "apps/fila/management/commands/desvincular_registros_fila.py"
    assert mi.curingas([caminho], backend) == [
        "apps.fila.management.commands.desvincular_registros_fila.*"
    ]


def test_teste_alterado_aponta_para_o_modulo_de_mesmo_nome(mi, backend):
    # É o caso do PR de prova: só o teste muda, e a mutação tem que rodar no
    # código que ele cobre.
    assert mi.curingas(
        ["apps/gamificacao/tests/test_patente_resolver.py"], backend
    ) == ["apps.gamificacao.patente_resolver.*"]


def test_teste_alterado_acha_o_modulo_dentro_do_leitor(mi, backend):
    assert mi.curingas(
        ["apps/cardapio/tests/test_cardapio_downloader.py"], backend
    ) == ["apps.cardapio.leitor.cardapio_downloader.*"]


def test_teste_do_leitor_aponta_para_o_leitor_inteiro(mi, backend):
    assert mi.curingas(["apps/cardapio/tests/test_leitor_pdf.py"], backend) == [
        "apps.cardapio.leitor.*"
    ]


def test_teste_sem_modulo_de_mesmo_nome_aponta_para_o_app_inteiro(mi, backend):
    assert mi.curingas(
        ["apps/gamificacao/tests/test_pontuacao_endpoints.py"], backend
    ) == ["apps.gamificacao.*"]


def test_apoio_dos_testes_aponta_para_o_app_inteiro(mi, backend):
    criar(backend, "apps/fila/tests/apoio.py")
    assert mi.curingas(["apps/fila/tests/apoio.py"], backend) == ["apps.fila.*"]


def test_apoio_do_leitor_aponta_para_o_leitor(mi, backend):
    assert mi.curingas(["apps/cardapio/tests/apoio_leitor.py"], backend) == [
        "apps.cardapio.leitor.*"
    ]


def test_teste_generico_do_cardapio_nao_muta_o_leitor(mi, backend):
    # O leitor tem quase metade dos mutantes da base: um PR de endpoint do
    # cardápio não pode estourar o tempo do job por causa dele.
    criar(backend, "apps/cardapio/tests/test_cardapio_endpoint.py")
    assert mi.curingas(["apps/cardapio/tests/test_cardapio_endpoint.py"], backend) == [
        "apps.cardapio.filtro_dieta_service.*"
    ]


def test_teste_apagado_ainda_roda_a_mutacao_do_modulo(mi, backend):
    # Apagar um teste pode derrubar o escore do módulo que ele cobria.
    (backend / "apps/gamificacao/tests/test_patente_resolver.py").unlink()
    assert mi.curingas(
        ["apps/gamificacao/tests/test_patente_resolver.py"], backend
    ) == ["apps.gamificacao.patente_resolver.*"]


@pytest.mark.parametrize(
    "caminho",
    [
        "apps/fila/migrations/0001_initial.py",
        "apps/fila/admin.py",
        "apps/fila/apps.py",
        "apps/fila/urls.py",
        "apps/fila/__init__.py",
        "apps/fila/tests/__init__.py",
        "tests/test_estrutura.py",
        "apps/__init__.py",
        "apps/fila/README.md",
        "apps/cardapio/fixtures/campi.json",
    ],
)
def test_arquivo_fora_da_mutacao_nao_gera_curinga(mi, backend, caminho):
    assert mi.curingas([caminho], backend) == []


def test_app_fora_dos_modulos_criticos_nao_gera_curinga(mi, backend):
    criar(backend, "apps/outro/servico.py")
    assert mi.curingas(["apps/outro/servico.py"], backend) == []


def test_arquivo_apagado_no_pr_nao_gera_curinga(mi, backend):
    # O `git diff` lista o arquivo apagado, mas não há mais código a mutar.
    assert mi.curingas(["apps/fila/servico_removido.py"], backend) == []


def test_curingas_sem_repeticao_e_em_ordem(mi, backend):
    alterados = [
        "apps/gamificacao/tests/test_patente_resolver.py",
        "apps/gamificacao/patente_resolver.py",
        "apps/fila/checkin_service.py",
    ]
    assert mi.curingas(alterados, backend) == [
        "apps.fila.checkin_service.*",
        "apps.gamificacao.patente_resolver.*",
    ]


def test_curinga_do_app_inteiro_engole_os_do_mesmo_app(mi, backend):
    criar(backend, "apps/fila/tests/apoio.py")
    alterados = [
        "apps/cardapio/leitor/cardapio_pdf_parser.py",
        "apps/cardapio/tests/apoio_leitor.py",
        "apps/fila/checkin_service.py",
        "apps/fila/tests/apoio.py",
    ]
    assert mi.curingas(alterados, backend) == [
        "apps.cardapio.leitor.*",
        "apps.fila.*",
    ]


# --- Mudança na configuração da mutação --------------------------------------


@pytest.mark.parametrize(
    "caminho",
    [
        "backend/setup.cfg",
        "backend/conftest.py",
        "backend/pytest.ini",
        "backend/requirements-dev.txt",
        "backend/scripts/mutacao_incremental.py",
        "backend/config/settings.py",
        ".github/workflows/backend-ci.yml",
    ],
)
def test_mudanca_na_configuracao_roda_o_alvo_fixo(mi, backend, caminho):
    # Sem isso, um PR que quebra a configuração do mutmut passaria verde sem
    # rodar nada (o próprio PR da BE-19 passou em 7 s).
    assert mi.curingas([caminho], backend) == [mi.ALVO_DA_CONFIGURACAO]


def test_alvo_fixo_junta_com_os_outros_alvos(mi, backend):
    alterados = ["backend/setup.cfg", "backend/apps/fila/checkin_service.py"]
    assert mi.curingas(alterados, backend) == sorted(
        ["apps.fila.checkin_service.*", mi.ALVO_DA_CONFIGURACAO]
    )


@pytest.mark.parametrize(
    "caminho",
    [
        "README.md",
        "docs/qualidade/plano-de-testes.md",
        ".github/workflows/frontend-ci.yml",
        ".github/workflows/backend-mutacao-semanal.yml",
        "frontend/package.json",
        "backend/Dockerfile",
    ],
)
def test_mudanca_fora_da_configuracao_nao_roda_nada(mi, backend, caminho):
    assert mi.curingas([caminho], backend) == []


def test_alvo_fixo_existe_no_backend_de_verdade(mi):
    modulo = mi.ALVO_DA_CONFIGURACAO.removesuffix(".*").replace(".", "/") + ".py"
    assert (RAIZ_BACKEND / modulo).is_file()


def test_init_dos_apps_criticos_nao_tem_codigo(mi):
    # O script não gera curinga para os `__init__.py` (o nome dos mutantes de
    # um `__init__.py` é o do pacote inteiro). Se um deles ganhar código, a
    # regra precisa mudar.
    for init in (RAIZ_BACKEND / "apps").glob("*/**/__init__.py"):
        caminho = init.relative_to(RAIZ_BACKEND)
        if caminho.parts[1] not in mi.APPS_CRITICOS or {"tests", "migrations"} & set(
            caminho.parts
        ):
            continue
        texto = init.read_text(encoding="utf-8")
        assert "def " not in texto and "class " not in texto, caminho


def test_sem_arquivo_critico_a_lista_fica_vazia(mi, backend):
    assert mi.curingas([], backend) == []


def test_os_apps_criticos_sao_os_do_setup_cfg(mi):
    # A lista do script e o only_mutate do setup.cfg não podem divergir.
    cfg = configparser.ConfigParser()
    cfg.read(SETUP_CFG, encoding="utf-8")
    only_mutate = cfg["mutmut"]["only_mutate"].split()
    assert sorted(f"apps/{app}/*" for app in mi.APPS_CRITICOS) == sorted(only_mutate)


# --- Arquivos alterados no git -----------------------------------------------


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repositorio(tmp_path):
    """Um repositório com `backend/` e uma base (`develop`) e um PR (`pr`)."""
    git(tmp_path, "init", "-q", "-b", "develop")
    git(tmp_path, "config", "user.email", "ci@example.invalid")
    git(tmp_path, "config", "user.name", "CI")
    criar(
        tmp_path,
        "backend/apps/fila/checkin_service.py",
        "backend/apps/fila/velho.py",
        "README.md",
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "pr")
    (tmp_path / "backend/apps/fila/checkin_service.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    (tmp_path / "backend/apps/fila/velho.py").unlink()
    (tmp_path / "README.md").write_text("mudou\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "pr")
    return tmp_path


def test_alterados_lista_tudo_relativo_a_raiz_do_repositorio(mi, repositorio):
    # Inclusive o que está fora de `backend/`: o workflow também é gatilho.
    alterados = mi.arquivos_alterados("develop", repositorio / "backend")
    assert sorted(alterados) == [
        "README.md",
        "backend/apps/fila/checkin_service.py",
        "backend/apps/fila/velho.py",
    ]


def test_alterados_ignora_o_que_mudou_so_na_base(mi, repositorio):
    # Base que andou depois que o PR saiu dela: com os três pontos, só conta o
    # que o PR mudou.
    git(repositorio, "checkout", "-q", "develop")
    criar(repositorio, "backend/apps/fila/da_base.py")
    git(repositorio, "add", ".")
    git(repositorio, "commit", "-q", "-m", "base andou")
    git(repositorio, "checkout", "-q", "pr")
    alterados = mi.arquivos_alterados("develop", repositorio / "backend")
    assert "backend/apps/fila/da_base.py" not in alterados


def test_comando_alvos_imprime_um_curinga_por_linha(repositorio):
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT), "alvos", "develop"],
        cwd=repositorio / "backend",
        capture_output=True,
        text=True,
        check=True,
    )
    assert resultado.stdout == "apps.fila.checkin_service.*\n"


def test_comando_alvos_sem_mudanca_no_backend_imprime_nada(repositorio):
    git(repositorio, "checkout", "-q", "-b", "so-readme", "develop")
    (repositorio / "README.md").write_text("outro\n", encoding="utf-8")
    git(repositorio, "commit", "-q", "-am", "readme")
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT), "alvos", "develop"],
        cwd=repositorio / "backend",
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0
    assert resultado.stdout == ""


def test_comando_alvos_falha_com_base_inexistente(repositorio):
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT), "alvos", "origin/nao-existe"],
        cwd=repositorio / "backend",
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 2
    assert resultado.stdout == ""
    assert "git diff" in resultado.stderr


# --- Curingas de cada módulo (rodada semanal) --------------------------------


def test_modulo_comum_e_o_app_inteiro(mi, backend):
    assert mi.curingas_do_modulo("fila", backend) == ["apps.fila.*"]


def test_modulo_do_leitor(mi, backend):
    assert mi.curingas_do_modulo("cardapio/leitor", backend) == [
        "apps.cardapio.leitor.*"
    ]


def test_modulo_cardapio_sem_o_leitor_lista_os_arquivos(mi, backend):
    # "apps.cardapio.*" também casaria com o leitor.
    criar(backend, "apps/cardapio/management/commands/ler_cardapio.py")
    assert mi.curingas_do_modulo("cardapio", backend) == [
        "apps.cardapio.filtro_dieta_service.*",
        "apps.cardapio.management.commands.ler_cardapio.*",
    ]


def test_modulo_desconhecido_e_erro(mi, backend):
    with pytest.raises(ValueError):
        mi.curingas_do_modulo("outro", backend)


def test_os_modulos_da_rodada_semanal_cobrem_os_seis_do_plano(mi):
    assert set(mi.MODULOS) == {
        "cadastro",
        "cardapio/leitor",
        "cardapio",
        "avaliacao",
        "fila",
        "gamificacao",
    }


# --- Escore ------------------------------------------------------------------


def stats(**valores):
    base = {
        "killed": 0,
        "survived": 0,
        "total": 5240,
        "no_tests": 0,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": 0,
        "segfault": 0,
    }
    base.update(valores)
    return base


def test_escore_e_mortos_sobre_avaliados_e_nao_sobre_o_total(mi):
    # O `total` conta todos os mutantes gerados, inclusive os que não rodaram
    # no modo incremental.
    resultado = mi.calcular_escore(stats(killed=30, survived=9))
    assert resultado.avaliados == 39
    assert resultado.mortos == 30
    assert resultado.escore == pytest.approx(30 / 39)


def test_timeout_conta_como_morto(mi):
    assert mi.calcular_escore(stats(killed=1, timeout=1, survived=2)).escore == 0.5


def test_sem_testes_conta_contra(mi):
    resultado = mi.calcular_escore(stats(killed=1, no_tests=3))
    assert resultado.avaliados == 4
    assert resultado.escore == 0.25


def test_suspeito_e_segfault_contam_contra(mi):
    assert mi.calcular_escore(stats(killed=2, suspicious=1, segfault=1)).escore == 0.5


def test_ignorados_ficam_fora(mi):
    assert mi.calcular_escore(stats(killed=1, skipped=10)).escore == 1.0


def test_nenhum_avaliado_nao_tem_escore(mi):
    resultado = mi.calcular_escore(stats())
    assert resultado.avaliados == 0
    assert resultado.escore is None


def rodar_escore(tmp_path, *args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_STEP_SUMMARY"}
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), "escore", *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def gravar(tmp_path, nome, dados):
    caminho = tmp_path / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


def test_comando_escore_falha_abaixo_do_minimo(tmp_path):
    gravar(tmp_path, "mutants/mutmut-cicd-stats.json", stats(killed=4, survived=6))
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 1
    assert "40,00%" in resultado.stdout


def test_comando_escore_passa_no_minimo(tmp_path):
    gravar(tmp_path, "mutants/mutmut-cicd-stats.json", stats(killed=5, survived=5))
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 0
    assert "50,00%" in resultado.stdout


def test_comando_escore_sem_avaliados_e_erro(tmp_path):
    # O passo de escore só roda depois que o mutmut testou mutantes: o "nada a
    # testar" é decidido antes, no job. Zero avaliados aqui é defeito.
    gravar(tmp_path, "mutants/mutmut-cicd-stats.json", stats())
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 2
    assert "nenhum mutante avaliado" in resultado.stderr


@pytest.mark.parametrize(
    "conteudo",
    [
        "{}",
        '{"total": 10}',
        '{"killed": 3}',
        "[]",
        "null",
        '{"killed": "abc", "survived": 1}',
        '{"killed": true, "survived": 1}',
        '{"killed": -1, "survived": 1}',
        '{"killed": 3, "survived": 1',
    ],
    ids=[
        "vazio",
        "sem-killed-e-survived",
        "sem-survived",
        "lista",
        "null",
        "texto",
        "booleano",
        "negativo",
        "truncado",
    ],
)
def test_comando_escore_json_invalido_e_erro(tmp_path, conteudo):
    # Um upgrade do mutmut que renomeie os campos não pode virar verde, nem
    # se confundir com "abaixo do mínimo" (saída 1).
    arquivo = tmp_path / "mutants" / "mutmut-cicd-stats.json"
    arquivo.parent.mkdir()
    arquivo.write_text(conteudo, encoding="utf-8")
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 2
    assert "Traceback" not in resultado.stderr


def test_comando_escore_rodada_interrompida_e_erro(tmp_path):
    # Interrompido no meio, o JSON é de uma amostra, e não da rodada inteira.
    gravar(
        tmp_path,
        "mutants/mutmut-cicd-stats.json",
        stats(killed=9, survived=1, check_was_interrupted_by_user=3),
    )
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 2
    assert "interrompid" in resultado.stderr


@pytest.mark.parametrize(("minimo", "saida"), [("50", 0), ("60", 0), ("70", 1)])
def test_comando_escore_respeita_o_minimo_pedido(tmp_path, minimo, saida):
    gravar(tmp_path, "mutants/mutmut-cicd-stats.json", stats(killed=6, survived=4))
    assert rodar_escore(tmp_path, "--minimo", minimo).returncode == saida


def test_comando_escore_logo_abaixo_do_minimo_nao_aparece_arredondado(tmp_path):
    gravar(
        tmp_path,
        "mutants/mutmut-cicd-stats.json",
        stats(killed=49999, survived=50001),
    )
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 1
    assert "49,99% ABAIXO DE 50%" in resultado.stdout


def test_comando_escore_sem_o_json_e_erro_e_nao_verde(tmp_path):
    # Se o mutmut quebrou antes de gravar o JSON, o job não pode passar.
    resultado = rodar_escore(tmp_path, "--minimo", "50")
    assert resultado.returncode == 2
    assert "mutmut-cicd-stats.json" in resultado.stderr


def test_comando_escore_grava_o_resumo_do_github(tmp_path):
    gravar(tmp_path, "mutants/mutmut-cicd-stats.json", stats(killed=30, survived=9))
    resumo = tmp_path / "resumo.md"
    rodar_escore(tmp_path, env_extra={"GITHUB_STEP_SUMMARY": str(resumo)})
    texto = resumo.read_text(encoding="utf-8")
    assert "| 30 | 0 | 9 | 0 | 0 | 0 | 39 | 76,92% |" in texto


def test_comando_escore_varios_modulos_falha_se_um_ficar_abaixo(tmp_path):
    # A meta vale para cada módulo crítico, e não só para a média.
    a = gravar(tmp_path, "a/stats.json", stats(killed=90, survived=10))
    b = gravar(tmp_path, "b/stats.json", stats(killed=4, survived=6))
    resultado = rodar_escore(tmp_path, "--minimo", "50", f"fila={a}", f"cadastro={b}")
    assert resultado.returncode == 1
    linhas = resultado.stdout.splitlines()
    linha_fila = next(linha for linha in linhas if linha.startswith("Mutação fila:"))
    linha_cadastro = next(
        linha for linha in linhas if linha.startswith("Mutação cadastro:")
    )
    assert "ABAIXO" not in linha_fila
    assert linha_cadastro.endswith("40,00% ABAIXO DE 50%")
    # Geral: 94 de 110.
    assert "Mutação geral: 94 de 110: 85,45%" in resultado.stdout


def test_comando_escore_varios_modulos_passa_com_todos_na_meta(tmp_path):
    a = gravar(tmp_path, "a/stats.json", stats(killed=90, survived=10))
    b = gravar(tmp_path, "b/stats.json", stats(killed=6, survived=4))
    resultado = rodar_escore(tmp_path, "--minimo", "50", f"fila={a}", f"cadastro={b}")
    assert resultado.returncode == 0


def test_comando_escore_varios_modulos_com_um_json_faltando_e_erro(tmp_path):
    # É o caso da rodada semanal em que o job de um módulo quebrou.
    a = gravar(tmp_path, "a/stats.json", stats(killed=90, survived=10))
    resultado = rodar_escore(
        tmp_path, "--minimo", "50", f"fila={a}", "cadastro=b/nao-existe.json"
    )
    assert resultado.returncode == 2
    assert "nao-existe.json" in resultado.stderr


def test_resumo_do_pr_fala_em_minimo_do_agregado(tmp_path):
    gravar(tmp_path, "mutants/mutmut-cicd-stats.json", stats(killed=30, survived=9))
    resumo = tmp_path / "resumo.md"
    rodar_escore(tmp_path, env_extra={"GITHUB_STEP_SUMMARY": str(resumo)})
    texto = resumo.read_text(encoding="utf-8")
    assert "em cada módulo" not in texto


# --- Conferência dos curingas -------------------------------------------------

RESULTADOS = """\
    apps.gamificacao.patente_resolver.xǁPatenteResolverǁ__init____mutmut_1: killed
    apps.gamificacao.patente_resolver.x_patente__mutmut_2: survived
    apps.fila.checkin_service.x_registrar__mutmut_1: not checked
"""


def rodar_conferir(tmp_path, alvos, resultados=RESULTADOS):
    (tmp_path / "alvos.txt").write_text(
        "".join(f"{a}\n" for a in alvos), encoding="utf-8"
    )
    (tmp_path / "resultados.txt").write_text(resultados, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "conferir", "alvos.txt", "resultados.txt"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_conferir_todos_os_curingas_casam(tmp_path):
    resultado = rodar_conferir(
        tmp_path,
        ["apps.gamificacao.patente_resolver.*", "apps.fila.checkin_service.*"],
    )
    assert resultado.returncode == 0
    assert "::warning::" not in resultado.stdout


def test_conferir_avisa_o_curinga_que_nao_casou(tmp_path):
    # Arquivo sem nada a mutar ou curinga com nome errado: não barra, mas
    # aparece como aviso na página do run.
    resultado = rodar_conferir(
        tmp_path,
        ["apps.gamificacao.patente_resolver.*", "apps.gamificacao.pontuacao_policy.*"],
    )
    assert resultado.returncode == 0
    assert "::warning::" in resultado.stdout
    assert "apps.gamificacao.pontuacao_policy.*" in resultado.stdout


def test_conferir_falha_se_o_formato_dos_nomes_mudou(tmp_path):
    # Se nenhum mutante começa com "apps.", o formato dos nomes mudou (upgrade
    # do mutmut ou source_paths): todo PR ficaria verde sem testar nada.
    resultados = "    gamificacao.patente_resolver.x_patente__mutmut_2: survived\n"
    resultado = rodar_conferir(
        tmp_path, ["apps.gamificacao.patente_resolver.*"], resultados
    )
    assert resultado.returncode == 2
    assert "::error::" in resultado.stdout


def test_conferir_falha_sem_nenhum_mutante_gerado(tmp_path):
    resultado = rodar_conferir(tmp_path, ["apps.gamificacao.patente_resolver.*"], "")
    assert resultado.returncode == 2


# --- O YAML e o script não podem divergir -------------------------------------


def carregar_yaml(nome):
    yaml = pytest.importorskip("yaml")
    caminho = RAIZ_BACKEND.parent / ".github" / "workflows" / nome
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def test_matriz_da_rodada_semanal_tem_os_modulos_do_script(mi):
    workflow = carregar_yaml("backend-mutacao-semanal.yml")
    matriz = workflow["jobs"]["mutacao"]["strategy"]["matrix"]["include"]
    assert sorted(item["modulo"] for item in matriz) == sorted(mi.MODULOS)


def test_escore_semanal_le_os_seis_modulos(mi):
    workflow = carregar_yaml("backend-mutacao-semanal.yml")
    passos = workflow["jobs"]["escore"]["steps"]
    comando = next(p["run"] for p in passos if "escore --minimo" in p.get("run", ""))
    rotulos = re.findall(r"(\S+)=relatorios/", comando)
    assert sorted(rotulos) == sorted(mi.MODULOS)
