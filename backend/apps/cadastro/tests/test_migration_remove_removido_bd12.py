"""BD-12: a migration 0004 não deixa uma conta "removida" voltar a ficar ativa.

Antes da revisão da ADR 0004, excluir a conta era marcar `status='removido'`.
A 0004 tira esse status e o `removido_em`; como `is_active` passou a ser
`status != 'suspenso'`, uma conta assim que sobrasse voltaria a entrar. A
migration recusa seguir enquanto houver uma, e a equipe a exclui antes.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

MIGRACAO_ANTERIOR = ("cadastro", "0003_tabela_do_cache")
MIGRACAO_BD12 = ("cadastro", "0004_remove_status_removido_bd12")


def migrar_para(destino):
    executor = MigrationExecutor(connection)
    executor.migrate([destino])
    return executor.loader.project_state([destino]).apps


@pytest.fixture
def estado_anterior(transactional_db):
    destinos_finais = MigrationExecutor(connection).loader.graph.leaf_nodes()

    try:
        yield migrar_para(MIGRACAO_ANTERIOR)
    finally:
        MigrationExecutor(connection).migrate(destinos_finais)


def criar_conta_historica(apps, numero, status):
    usuario = apps.get_model("cadastro", "Usuario")
    apelido = f"antiga{numero}"

    return usuario.objects.using(connection.alias).create(
        matricula_siape=f"{numero:09d}",
        tipo_usuario="estudante",
        apelido=apelido,
        apelido_normalizado=apelido,
        email_institucional=f"{apelido}@aluno.unb.br",
        password="!",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste-bd12",
        status=status,
    )


def test_migration_recusa_conta_removida_e_nao_muda_nada(estado_anterior):
    removida = criar_conta_historica(estado_anterior, 1, "removido")
    criar_conta_historica(estado_anterior, 2, "ativo")

    try:
        with pytest.raises(RuntimeError, match="remover_conta") as erro:
            migrar_para(MIGRACAO_BD12)

        assert "1 conta(s)" in str(erro.value)
        assert str(removida.pk) in str(erro.value)
        assert f"ids: {removida.pk}" in str(erro.value) or str(removida.pk) in str(
            erro.value
        )
        # Nada foi aplicado: a conta continua como estava, e a coluna também.
        usuario = estado_anterior.get_model("cadastro", "Usuario")
        assert usuario.objects.get(pk=removida.pk).status == "removido"
        assert any(
            c.name == "removido_em"
            for c in connection.introspection.get_table_description(
                connection.cursor(), usuario._meta.db_table
            )
        )
    finally:
        # O fixture volta ao estado final, e a migration recusaria de novo.
        estado_anterior.get_model("cadastro", "Usuario").objects.filter(
            pk=removida.pk
        ).delete()


def test_migration_segue_sem_conta_removida_e_mantem_os_outros_status(estado_anterior):
    criar_conta_historica(estado_anterior, 1, "ativo")
    criar_conta_historica(estado_anterior, 2, "suspenso")
    criar_conta_historica(estado_anterior, 3, "pendente")

    novo = migrar_para(MIGRACAO_BD12)

    usuario = novo.get_model("cadastro", "Usuario")
    assert "removido_em" not in {campo.name for campo in usuario._meta.get_fields()}
    status = dict(usuario.objects.values_list("matricula_siape", "status"))
    assert status == {
        "000000001": "ativo",
        "000000002": "suspenso",
        "000000003": "pendente",
    }
