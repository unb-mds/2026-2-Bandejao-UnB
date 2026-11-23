"""Inicializa a pontuação das contas existentes sem alterar contadores."""

from django.db import migrations


def inicializar_pontuacao_usuarios(apps, schema_editor):
    usuario = apps.get_model("cadastro", "Usuario")
    pontuacao_usuario = apps.get_model("gamificacao", "PontuacaoUsuario")
    banco = schema_editor.connection.alias

    usuarios = usuario.objects.using(banco).values_list("pk", flat=True)

    for usuario_id in usuarios.iterator(chunk_size=500):
        pontuacao_usuario.objects.using(banco).get_or_create(
            usuario_id=usuario_id,
            defaults={
                "pontos_totais": 0,
                "sequencia_atual": 0,
                "ultima_semana_completada": None,
                "participa_ranking": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = (
        ("cadastro", "0002_usuario_primeira_falha_login_em"),
        ("gamificacao", "0001_initial"),
    )

    # Reverter esta migration não apaga contadores: eles podem ter recebido
    # pontos depois da inicialização.
    operations = (
        migrations.RunPython(
            inicializar_pontuacao_usuarios,
            reverse_code=migrations.RunPython.noop,
        ),
    )
