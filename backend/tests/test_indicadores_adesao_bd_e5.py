"""BD-E5: as quatro consultas dos indicadores de adesão (RNF09) dão o número certo.

As consultas ficam em
docs/arquitetura/banco-de-dados/indicadores-adesao-bd-e5.md e este teste as lê
de lá: o que a equipe cola no MySQL de produção é exatamente o que foi
testado. Roda nos jobs `testes` (SQLite) e `testes-mysql` (MySQL 8.4).

Os dados são pequenos e a resposta de cada indicador é conhecida de antemão
(docstring da fixture `dados`). Há registros fora da janela, contas suspensas
e pendentes, check-ins sem conta e conta sem linha de pontos, para um filtro
esquecido ou um JOIN que descarta linhas mudar o número.

O `SET @inicio` do documento não é executado no SQLite (a função de data é do
MySQL). Por isso ele é conferido de duas formas: o texto tem de seguir o
formato esperado, com o deslocamento de Brasília e os dias da janela ligados
aos parâmetros do backend, e, no `testes-mysql`, o comando roda de verdade e o
valor de `@inicio` é comparado com o dia de Brasília.
"""

import re
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from apps.cadastro.models import StatusUsuario
from apps.cardapio.models import TipoRefeicao
from apps.fila.models import Checkin, EstadoPergunta, PerguntaSaida
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontuacaoUsuario
from config.parametros import ParametrosFilaConfig

DOC = (
    Path(__file__).resolve().parents[2]
    / "docs/arquitetura/banco-de-dados/indicadores-adesao-bd-e5.md"
)
SEMANAS = ParametrosFilaConfig.retencao_semanas
# A janela são as `SEMANAS` semanas mais recentes: 28 datas, de hoje até
# hoje - 27 dias. O primeiro dia da janela (`inicio()`) fica dentro dela.
DIAS_ATRAS = SEMANAS * 7 - 1
SET_INICIO = re.compile(
    r"^SET @inicio = DATE\(UTC_TIMESTAMP\(\) - INTERVAL (\d+) HOUR\)"
    r" - INTERVAL (\d+) DAY;$"
)


def hoje():
    """O dia de Brasília, o mesmo que o `SET @inicio` do documento calcula."""
    return timezone.localdate()


def inicio():
    return hoje() - timedelta(days=DIAS_ATRAS)


def blocos_sql():
    """Os blocos `sql` do documento, reconhecidos pelo começo do texto.

    Devolve o `SET @inicio`, o trecho que restringe as consultas 3 e 4 a quem
    fez check-in na janela e as quatro consultas, na ordem do documento.
    """
    blocos = re.findall(r"```sql\n(.*?)```", DOC.read_text(encoding="utf-8"), re.DOTALL)
    assert len(blocos) == 6
    set_inicio = [b for b in blocos if b.startswith("SET @inicio")]
    trecho = [b for b in blocos if b.startswith("AND EXISTS")]
    consultas = [b for b in blocos if b.startswith("SELECT")]
    assert len(set_inicio) == len(trecho) == 1
    assert len(consultas) == 4
    return set_inicio[0], trecho[0], consultas


def consultas():
    return blocos_sql()[2]


def rodar(numero, base_so_de_quem_fez_checkin=False):
    sql = consultas()[numero - 1]
    if base_so_de_quem_fez_checkin:
        antes = "WHERE u.status = 'ativo';"
        assert antes in sql
        trecho = blocos_sql()[1].strip()
        sql = sql.replace(antes, f"WHERE u.status = 'ativo'\n  {trecho};")
    sql = sql.replace("@inicio", "%(inicio)s")
    with connection.cursor() as cursor:
        cursor.execute(sql, {"inicio": inicio()})
        colunas = [c[0] for c in cursor.description]
        linhas = cursor.fetchall()
    assert len(linhas) == 1
    return dict(zip(colunas, linhas[0], strict=True))


def _conta(n, status):
    return get_user_model().objects.create_user(
        matricula_siape=f"2026{n:05d}",
        tipo_usuario="estudante",
        apelido=f"conta{n}",
        email_institucional=f"2026{n:05d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
        status=status,
    )


def _checkin(campus, conta, dia, tipo, estado=None):
    checkin = Checkin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao=tipo,
        data=dia,
        registrado_em=None,
        faixa_inicio=time(11, 30),
    )
    if estado is not None:
        base = datetime.combine(
            dia, time(11, 30), tzinfo=timezone.get_current_timezone()
        )
        PerguntaSaida.objects.create(
            checkin=checkin,
            estado=estado,
            devida_em=base + timedelta(minutes=15),
            expira_em=base + timedelta(minutes=60),
        )
    return checkin


def _pontos(conta, sequencia, ranking):
    PontuacaoUsuario.objects.create(
        usuario=conta, sequencia_atual=sequencia, participa_ranking=ranking
    )


@pytest.fixture
def dados(db):
    """Resposta esperada de cada indicador (janela de 28 datas, de `inicio()`
    até hoje):

    1. 15 check-ins na janela, 4 com a pergunta respondida (3 dispensadas, 6
       pendentes e 2 sem linha de pergunta): 26,7%. Os três estados têm
       contagens diferentes, para trocar um pelo outro mudar o número.
    2. 13 check-ins com conta, de 6 contas (a, b, c, f, g e a suspensa, que
       conta): 13 / (6 x 4 semanas) = 0,54. A conta f não tem linha de pontos.
    3. 6 contas ativas (a, b, c, f, g, h), 4 com sequência de 2 ou mais
       (a, b, g, h): 66,7%.
    4. As mesmas 6 contas, 2 no ranking (a, c): 33,3%.

    Só entre quem fez check-in na janela (variante do documento): 5 contas
    (a, b, c, f, g; h só tem check-in antes da janela), 3 com sequência
    (a, b, g) = 60,0% e 2 no ranking (a, c) = 40,0%.
    """
    campus = criar_campus()
    a = _conta(1, StatusUsuario.ATIVO)
    b = _conta(2, StatusUsuario.ATIVO)
    c = _conta(3, StatusUsuario.ATIVO)
    suspensa = _conta(4, StatusUsuario.SUSPENSO)
    _conta(5, StatusUsuario.PENDENTE)
    f = _conta(6, StatusUsuario.ATIVO)  # ativa e sem linha de pontos
    g = _conta(7, StatusUsuario.ATIVO)
    h = _conta(8, StatusUsuario.ATIVO)

    _pontos(a, sequencia=3, ranking=True)
    _pontos(b, sequencia=2, ranking=False)
    _pontos(c, sequencia=1, ranking=True)
    _pontos(g, sequencia=4, ranking=False)
    _pontos(h, sequencia=2, ranking=False)
    # Suspensa e adepta com sequência alta: fica fora da base dos indicadores 3 e 4.
    _pontos(suspensa, sequencia=9, ranking=True)

    almoco, jantar = TipoRefeicao.ALMOCO, TipoRefeicao.JANTAR
    R, P, D = (
        EstadoPergunta.RESPONDIDA,
        EstadoPergunta.PENDENTE,
        EstadoPergunta.DISPENSADA,
    )
    d = inicio()
    # Dentro da janela, com conta (13): a x5, b x1, c x3, g x1, suspensa x1, f x2.
    # O primeiro é do primeiro dia da janela e o último de hoje (as pontas).
    _checkin(campus, a, d, almoco, R)
    _checkin(campus, a, d + timedelta(days=1), almoco, R)
    _checkin(campus, a, d + timedelta(days=1), jantar, P)
    _checkin(campus, a, d + timedelta(days=7), almoco, D)
    _checkin(campus, a, hoje(), almoco, R)
    _checkin(campus, b, d + timedelta(days=2), almoco, R)
    _checkin(campus, c, d + timedelta(days=3), almoco, P)
    _checkin(campus, c, d + timedelta(days=4), almoco, D)
    _checkin(campus, c, d + timedelta(days=6), almoco, D)
    _checkin(campus, g, d + timedelta(days=9), almoco, P)
    _checkin(campus, suspensa, d + timedelta(days=8), almoco, P)
    _checkin(campus, f, d + timedelta(days=10), almoco, P)
    _checkin(campus, f, d + timedelta(days=10), jantar, P)
    # Dentro da janela, sem conta (2), sem linha de pergunta: contam só no 1.
    _checkin(campus, None, d + timedelta(days=5), almoco)
    _checkin(campus, None, d + timedelta(days=5), jantar)
    # Um dia antes da janela: não entram em nenhum indicador. O de h é o único
    # dela: sem o filtro de data, a variante do documento a contaria.
    _checkin(campus, c, d - timedelta(days=1), almoco, R)
    _checkin(campus, h, d - timedelta(days=1), almoco, R)
    _checkin(campus, None, d - timedelta(days=1), jantar, R)


def test_pergunta_de_saida_respondida(dados):
    r = rodar(1)

    assert r["checkins"] == 15
    assert r["respondidas"] == 4
    assert float(r["pct_respondidas"]) == pytest.approx(26.7)


def test_checkins_por_usuario_ativo_por_semana(dados):
    r = rodar(2)

    assert r["checkins"] == 13
    assert r["usuarios_ativos"] == 6
    assert float(r["checkins_por_usuario_por_semana"]) == pytest.approx(0.54)


def test_sequencia_de_duas_semanas_ou_mais(dados):
    r = rodar(3)

    assert r["contas_ativas"] == 6
    assert r["com_sequencia"] == 4
    assert float(r["pct_com_sequencia"]) == pytest.approx(66.7)


def test_adesao_ao_ranking(dados):
    r = rodar(4)

    assert r["contas_ativas"] == 6
    assert r["no_ranking"] == 2
    assert float(r["pct_no_ranking"]) == pytest.approx(33.3)


def test_base_so_de_quem_fez_checkin_na_janela(dados):
    sequencia = rodar(3, base_so_de_quem_fez_checkin=True)
    ranking = rodar(4, base_so_de_quem_fez_checkin=True)

    assert sequencia["contas_ativas"] == 5
    assert sequencia["com_sequencia"] == 3
    assert float(sequencia["pct_com_sequencia"]) == pytest.approx(60.0)
    assert ranking["contas_ativas"] == 5
    assert ranking["no_ranking"] == 2
    assert float(ranking["pct_no_ranking"]) == pytest.approx(40.0)


def test_sem_nenhum_dado_as_contagens_saem_zero_e_as_porcentagens_nulas(db):
    esperado = (
        (1, {"checkins": 0, "respondidas": 0}, "pct_respondidas"),
        (2, {"checkins": 0, "usuarios_ativos": 0}, "checkins_por_usuario_por_semana"),
        (3, {"contas_ativas": 0, "com_sequencia": 0}, "pct_com_sequencia"),
        (4, {"contas_ativas": 0, "no_ranking": 0}, "pct_no_ranking"),
    )
    for numero, contagens, porcentagem in esperado:
        r = rodar(numero)
        for coluna, valor in contagens.items():
            assert r[coluna] == valor
        assert r[porcentagem] is None


def test_as_consultas_usam_os_nomes_de_tabela_dos_models():
    texto = "\n".join(consultas())

    for modelo in (Checkin, PerguntaSaida, PontuacaoUsuario, get_user_model()):
        assert modelo._meta.db_table in texto


def test_set_inicio_segue_o_formato_e_os_parametros_do_backend():
    comando = blocos_sql()[0].strip()
    achou = SET_INICIO.match(comando)

    assert achou, f"o SET @inicio mudou de formato: {comando!r}"
    horas, dias = int(achou.group(1)), int(achou.group(2))
    # Brasília não tem horário de verão desde 2019: o deslocamento é fixo.
    deslocamento = datetime.now(ZoneInfo("America/Sao_Paulo")).utcoffset()
    assert timedelta(hours=-horas) == deslocamento
    assert dias == DIAS_ATRAS


def test_semanas_da_consulta_2_sao_as_da_retencao():
    sql = consultas()[1]
    achou = re.search(r"COUNT\(DISTINCT c\.usuario_id\) \* (\d+)", sql)

    assert achou
    assert int(achou.group(1)) == SEMANAS


@pytest.mark.skipif(
    connection.vendor != "mysql", reason="UTC_TIMESTAMP() e INTERVAL são do MySQL"
)
def test_set_inicio_no_mysql_da_o_inicio_da_janela_em_brasilia(db):
    with connection.cursor() as cursor:
        cursor.execute(blocos_sql()[0])
        cursor.execute("SELECT @inicio")
        (valor,) = cursor.fetchone()

    # O MySQL devolve variável de usuário como texto ('2026-10-28'), e não como
    # data: compara-se a data escrita por extenso.
    assert str(valor) == inicio().isoformat()
