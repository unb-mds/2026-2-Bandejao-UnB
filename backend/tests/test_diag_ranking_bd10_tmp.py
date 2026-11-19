"""Diagnóstico TEMPORÁRIO da BD-10 (#150): plano da consulta do ranking com
`select_related("usuario")` no MySQL. Será removido no próximo commit."""

import pytest
from django.db import connection

from tests.test_indices_bd10 import consulta_ranking, dados_de_teste  # noqa: F401


@pytest.mark.skipif(connection.vendor != "mysql", reason="Só MySQL.")
def test_diagnostico_ranking_com_select_related(dados_de_teste):  # noqa: F811
    consulta = consulta_ranking(dados_de_teste[2])._chain()
    consulta.query.add_select_related(["usuario"])
    sql, parametros = consulta.query.sql_with_params()
    print("\n##### 9 ranking (CASE/EXISTS) com select_related")
    with connection.cursor() as cursor:
        for prefixo in ("EXPLAIN", "EXPLAIN FORMAT=TREE"):
            cursor.execute(f"{prefixo} {sql}", parametros)
            colunas = [c[0] for c in cursor.description]
            for linha in cursor.fetchall():
                print(f"  {dict(zip(colunas, linha))}")
