"""Diagnóstico TEMPORÁRIO da BD-10 (#150): planos de variantes da consulta do
ranking no MySQL. Será removido depois de escolhida a forma da consulta."""

import pytest
from django.db import connection
from django.db.models import Exists, OuterRef

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

    variantes = {
        "1 join (atual), com ANALYZE de todas as tabelas": _base(campus).filter(
            usuario__status=StatusUsuario.ATIVO,
            usuario__pontuacao__participa_ranking=True,
        ),
        "2 exists": _base(campus).filter(
            Exists(
                PontuacaoUsuario.objects.filter(
                    usuario_id=OuterRef("usuario_id"),
                    participa_ranking=True,
                    usuario__status=StatusUsuario.ATIVO,
                )
            )
        ),
        "3 usuario__in subquery": _base(campus).filter(
            usuario__in=PontuacaoUsuario.objects.filter(
                participa_ranking=True, usuario__status=StatusUsuario.ATIVO
            ).values("usuario_id")
        ),
        "4 só a tabela de pontos (sem elegibilidade)": _base(campus),
    }
    for rotulo, qs in variantes.items():
        sql, parametros = qs.order_by(*ORDEM)[:10].query.sql_with_params()
        _explicar(rotulo, sql, parametros)

    sql, parametros = (
        variantes["1 join (atual), com ANALYZE de todas as tabelas"]
        .order_by(*ORDEM)[:10]
        .query.sql_with_params()
    )
    for dica in (
        "/*+ JOIN_ORDER(gamificacao_pontossemestrecampus) */",
        "/*+ INDEX(gamificacao_pontossemestrecampus pontos_semestre_ranking_idx) */",
    ):
        _explicar(
            f"5 join com dica {dica}",
            sql.replace("SELECT", f"SELECT {dica}", 1),
            parametros,
        )
