"""Apoio dos testes do ranking (BE-17): contas e linhas de pontos gravadas
direto no banco, com o desempate (`atualizado_em`) fixo."""

from datetime import UTC, datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cadastro.models import StatusUsuario
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario

SEMESTRE = "2026.2"
INICIO = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def criar_conta(numero, aderiu=True, status=StatusUsuario.ATIVO):
    conta = get_user_model().objects.create_user(
        matricula_siape=f"2024002{numero:02d}",
        tipo_usuario="estudante",
        apelido=f"conta{numero:02d}",
        email_institucional=f"2024002{numero:02d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
    get_user_model().objects.filter(pk=conta.pk).update(status=status)
    PontuacaoUsuario.objects.create(usuario=conta, participa_ranking=aderiu)
    return conta


def pontuar(conta, campus, pontos, minutos=0, semestre=SEMESTRE):
    """Linha de pontos com `atualizado_em` fixo. O `update()` não dispara o
    `auto_now`, por isso fixa o desempate."""
    linha = PontosSemestreCampus.objects.create(
        usuario=conta, campus=campus, semestre_referencia=semestre, pontos=pontos
    )
    PontosSemestreCampus.objects.filter(pk=linha.pk).update(
        atualizado_em=INICIO + timedelta(minutes=minutos)
    )
    return linha
