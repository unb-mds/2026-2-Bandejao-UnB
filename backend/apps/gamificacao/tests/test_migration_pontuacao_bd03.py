"""BD-03: inicialização da pontuação das contas existentes."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

MIGRACAO_ANTERIOR = ("gamificacao", "0001_initial")
MIGRACAO_BD03 = ("gamificacao", "0002_inicializar_pontuacao_usuarios")
# O esquema de `cadastro` na época da BD-03 (antes da BD-12 remover `removido_em`).
CADASTRO_NA_EPOCA = ("cadastro", "0003_tabela_do_cache")


def migrar_para(destino):
    alvos = [destino, CADASTRO_NA_EPOCA]
    executor = MigrationExecutor(connection)
    executor.migrate(alvos)
    return executor.loader.project_state(alvos).apps


@pytest.fixture
def estado_anterior(transactional_db):
    destinos_finais = MigrationExecutor(connection).loader.graph.leaf_nodes()

    try:
        yield migrar_para(MIGRACAO_ANTERIOR)
    finally:
        MigrationExecutor(connection).migrate(destinos_finais)


def criar_conta_historica(apps, numero):
    usuario = apps.get_model("cadastro", "Usuario")
    apelido = f"legado{numero}"

    return usuario.objects.using(connection.alias).create(
        matricula_siape=f"{numero:09d}",
        tipo_usuario="estudante",
        apelido=apelido,
        apelido_normalizado=apelido,
        email_institucional=f"{apelido}@aluno.unb.br",
        password="!",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste-bd03",
    )


def test_migration_cria_pontuacao_zerada_para_contas_existentes(
    estado_anterior,
):
    contas = [
        criar_conta_historica(estado_anterior, 1),
        criar_conta_historica(estado_anterior, 2),
    ]
    pontuacao_anterior = estado_anterior.get_model("gamificacao", "PontuacaoUsuario")
    assert pontuacao_anterior.objects.count() == 0

    estado_novo = migrar_para(MIGRACAO_BD03)
    pontuacao = estado_novo.get_model("gamificacao", "PontuacaoUsuario")

    assert pontuacao.objects.count() == 2
    assert set(pontuacao.objects.values_list("usuario_id", flat=True)) == {
        conta.pk for conta in contas
    }

    for registro in pontuacao.objects.all():
        assert registro.pontos_totais == 0
        assert registro.sequencia_atual == 0
        assert registro.ultima_semana_completada is None
        assert registro.participa_ranking is False
        assert registro.atualizado_em is not None


def test_migration_preserva_pontos_e_reaplicacao_nao_duplica(
    estado_anterior,
):
    conta_com_pontos = criar_conta_historica(estado_anterior, 1)
    conta_sem_pontos = criar_conta_historica(estado_anterior, 2)
    pontuacao_anterior = estado_anterior.get_model("gamificacao", "PontuacaoUsuario")
    existente = pontuacao_anterior.objects.create(
        usuario_id=conta_com_pontos.pk,
        pontos_totais=80,
        sequencia_atual=2,
        participa_ranking=True,
    )
    valores_originais = pontuacao_anterior.objects.values().get(pk=existente.pk)

    estado_novo = migrar_para(MIGRACAO_BD03)
    pontuacao = estado_novo.get_model("gamificacao", "PontuacaoUsuario")

    assert pontuacao.objects.count() == 2
    assert pontuacao.objects.values().get(pk=existente.pk) == valores_originais
    assert pontuacao.objects.get(usuario_id=conta_sem_pontos.pk).pontos_totais == 0

    valores_antes = list(pontuacao.objects.order_by("usuario_id").values())

    estado_revertido = migrar_para(MIGRACAO_ANTERIOR)
    pontuacao_revertida = estado_revertido.get_model("gamificacao", "PontuacaoUsuario")
    assert (
        list(pontuacao_revertida.objects.order_by("usuario_id").values())
        == valores_antes
    )

    estado_reaplicado = migrar_para(MIGRACAO_BD03)
    pontuacao_reaplicada = estado_reaplicado.get_model(
        "gamificacao", "PontuacaoUsuario"
    )

    assert pontuacao_reaplicada.objects.count() == 2
    assert (
        list(pontuacao_reaplicada.objects.order_by("usuario_id").values())
        == valores_antes
    )
