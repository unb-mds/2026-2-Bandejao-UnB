"""BD-E5: as quatro consultas dos indicadores de adesão (RNF09) dão o número certo.

As consultas ficam em
docs/arquitetura/banco-de-dados/indicadores-adesao-bd-e5.md e este teste as lê
de lá: o que a equipe cola no MySQL de produção é exatamente o que foi
testado. Roda nos jobs `testes` (SQLite) e `testes-mysql` (MySQL 8.4).

Os dados são pequenos e a resposta de cada indicador é conhecida de antemão
(comentários em `_criar_dados`). Há registros fora da janela, contas
suspensas e pendentes, check-ins sem conta e conta sem linha de pontos, para
um filtro esquecido ou um JOIN que descarta linhas mudar o número.
"""

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from apps.cadastro.models import StatusUsuario
from apps.cardapio.models import TipoRefeicao
from apps.fila.models import Checkin, EstadoPergunta, PerguntaSaida
from apps.fila.tests.apoio import criar_campus
from apps.gamificacao.models import PontuacaoUsuario

DOC = (
    Path(__file__).resolve().parents[2]
    / "docs/arquitetura/banco-de-dados/indicadores-adesao-bd-e5.md"
)
HOJE = date(2026, 11, 24)
INICIO = HOJE - timedelta(days=28)  # 27/10, o dia-limite fica (como na retenção)


def consultas():
    """Os blocos `sql` do documento: o `SET @inicio` e as quatro consultas."""
    blocos = re.findall(r"```sql\n(.*?)```", DOC.read_text(encoding="utf-8"), re.DOTALL)
    assert len(blocos) == 5
    assert blocos[0].startswith("SET @inicio")
    return blocos[1:]


def rodar(numero):
    sql = consultas()[numero - 1].replace("@inicio", "%(inicio)s")
    with connection.cursor() as cursor:
        cursor.execute(sql, {"inicio": INICIO})
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


@pytest.fixture
def dados(db):
    """Resposta esperada de cada indicador (janela a partir de 27/10):

    1. 9 check-ins na janela, 3 com a pergunta respondida: 33,3%.
    2. 7 check-ins com conta, de 3 contas: 7 / (3 x 4 semanas) = 0,58.
    3. 4 contas ativas (a, b, c, f), 2 com sequência de 2 ou mais (a, b): 50,0%.
    4. As mesmas 4 contas, 2 no ranking (a, c): 50,0%.
    """
    campus = criar_campus()
    a = _conta(1, StatusUsuario.ATIVO)
    b = _conta(2, StatusUsuario.ATIVO)
    c = _conta(3, StatusUsuario.ATIVO)
    suspensa = _conta(4, StatusUsuario.SUSPENSO)
    _conta(5, StatusUsuario.PENDENTE)
    _conta(6, StatusUsuario.ATIVO)  # f: ativa e sem linha de pontos

    PontuacaoUsuario.objects.create(
        usuario=a, sequencia_atual=3, participa_ranking=True
    )
    PontuacaoUsuario.objects.create(
        usuario=b, sequencia_atual=2, participa_ranking=False
    )
    PontuacaoUsuario.objects.create(
        usuario=c, sequencia_atual=1, participa_ranking=True
    )
    # Suspensa e adepta com sequência alta: fica fora da base dos indicadores 3 e 4.
    PontuacaoUsuario.objects.create(
        usuario=suspensa, sequencia_atual=9, participa_ranking=True
    )

    almoco, jantar = TipoRefeicao.ALMOCO, TipoRefeicao.JANTAR
    R, P, D = (
        EstadoPergunta.RESPONDIDA,
        EstadoPergunta.PENDENTE,
        EstadoPergunta.DISPENSADA,
    )
    d = INICIO
    # Dentro da janela, com conta (7): a x4, b x1, c x2. O primeiro é do dia-limite.
    _checkin(campus, a, d, almoco, R)
    _checkin(campus, a, d + timedelta(days=1), almoco, R)
    _checkin(campus, a, d + timedelta(days=1), jantar, P)
    _checkin(campus, a, d + timedelta(days=7), almoco, D)
    _checkin(campus, b, d + timedelta(days=2), almoco, R)
    _checkin(campus, c, d + timedelta(days=3), almoco, P)
    _checkin(campus, c, d + timedelta(days=4), almoco, D)
    # Dentro da janela, sem conta (2), sem linha de pergunta: contam só no 1.
    _checkin(campus, None, d + timedelta(days=5), almoco)
    _checkin(campus, None, d + timedelta(days=5), jantar)
    # Um dia antes da janela: não entram em nenhum indicador.
    _checkin(campus, c, d - timedelta(days=1), almoco, R)
    _checkin(campus, None, d - timedelta(days=1), jantar, R)


def test_pergunta_de_saida_respondida(dados):
    r = rodar(1)

    assert r["checkins"] == 9
    assert r["respondidas"] == 3
    assert float(r["pct_respondidas"]) == pytest.approx(33.3)


def test_checkins_por_usuario_ativo_por_semana(dados):
    r = rodar(2)

    assert r["checkins"] == 7
    assert r["usuarios_ativos"] == 3
    assert float(r["checkins_por_usuario_por_semana"]) == pytest.approx(0.58)


def test_sequencia_de_duas_semanas_ou_mais(dados):
    r = rodar(3)

    assert r["contas_ativas"] == 4
    assert r["com_sequencia"] == 2
    assert float(r["pct_com_sequencia"]) == pytest.approx(50.0)


def test_adesao_ao_ranking(dados):
    r = rodar(4)

    assert r["contas_ativas"] == 4
    assert r["no_ranking"] == 2
    assert float(r["pct_no_ranking"]) == pytest.approx(50.0)


def test_sem_nenhum_dado_as_porcentagens_saem_nulas_e_nao_dao_erro(db):
    for numero, coluna in (
        (1, "pct_respondidas"),
        (2, "checkins_por_usuario_por_semana"),
        (3, "pct_com_sequencia"),
        (4, "pct_no_ranking"),
    ):
        assert rodar(numero)[coluna] is None


def test_as_consultas_usam_os_nomes_de_tabela_dos_models():
    texto = "\n".join(consultas())

    for modelo in (Checkin, PerguntaSaida, PontuacaoUsuario, get_user_model()):
        assert modelo._meta.db_table in texto
