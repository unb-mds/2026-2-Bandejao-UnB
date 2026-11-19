"""Diagnóstico TEMPORÁRIO da BD-10 (#150): planos de variantes da consulta do
ranking no MySQL. Será removido depois de escolhida a forma da consulta."""

import pytest
from django.db import connection
from django.db.models import Case, Exists, OuterRef, Value, When

from apps.cadastro.models import StatusUsuario
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from tests.test_indices_bd10 import dados_de_teste  # noqa: F401


def _explicar(rotulo, sql, parametros):
    print(f"\n##### {rotulo}")
    with connection.cursor() as cursor:
        for prefixo in ("EXPLAIN", "EXPLAIN FORMAT=TREE"):
            cursor.execute(f"{prefixo} {sql}", parametros)
            colunas = [c[0] for c in cursor.description]
            for linha in cursor.fetchall():
                print(f"  {dict(zip(colunas, linha))}")


def _base(campus):
    return PontosSemestreCampus.objects.filter(
        campus=campus, semestre_referencia="2026.2", pontos__gte=1
    )


ORDEM = ("-pontos", "atualizado_em")


@pytest.mark.skipif(connection.vendor != "mysql", reason="Só MySQL.")
def test_diagnostico_variantes_ranking(dados_de_teste):  # noqa: F811
    campus = dados_de_teste[2]
    with connection.cursor() as cursor:
        cursor.execute(
            "ANALYZE TABLE gamificacao_pontuacaousuario, cadastro_usuario, "
            "gamificacao_pontossemestrecampus"
        )
        cursor.fetchall()

    elegivel = Exists(
        PontuacaoUsuario.objects.filter(
            usuario_id=OuterRef("usuario_id"),
            participa_ranking=True,
            usuario__status=StatusUsuario.ATIVO,
        )
    )
    juncao = _base(campus).filter(
        usuario__status=StatusUsuario.ATIVO,
        usuario__pontuacao__participa_ranking=True,
    )
    variantes = {
        "6 exists dentro de CASE": _base(campus)
        .annotate(elegivel=Case(When(elegivel, then=Value(1)), default=Value(0)))
        .filter(elegivel=1),
    }
    for rotulo, qs in variantes.items():
        sql, parametros = qs.order_by(*ORDEM)[:10].query.sql_with_params()
        _explicar(rotulo, sql, parametros)

    sql, parametros = juncao.order_by(*ORDEM)[:10].query.sql_with_params()
    _explicar(
        "7 join com JOIN_PREFIX",
        sql.replace(
            "SELECT",
            "SELECT /*+ JOIN_PREFIX(gamificacao_pontossemestrecampus) */",
            1,
        ),
        parametros,
    )

    with connection.cursor() as cursor:
        cursor.execute("ANALYZE TABLE cadastro_usuario UPDATE HISTOGRAM ON status")
        cursor.fetchall()
        cursor.execute(
            "ANALYZE TABLE gamificacao_pontuacaousuario "
            "UPDATE HISTOGRAM ON participa_ranking"
        )
        cursor.fetchall()
    _explicar("8 join com histogramas", sql, parametros)

    # Não deixa os histogramas para os outros testes.
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE TABLE cadastro_usuario DROP HISTOGRAM ON status")
        cursor.fetchall()
        cursor.execute(
            "ANALYZE TABLE gamificacao_pontuacaousuario "
            "DROP HISTOGRAM ON participa_ranking"
        )
        cursor.fetchall()
