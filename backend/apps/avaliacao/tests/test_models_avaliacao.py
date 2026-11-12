"""Testes do model `Avaliacao` (BD-01, parte 3).

Cada teste vem de uma regra do Nível 4 do banco (dicionário de dados e tabela
"Constraints principais"): RF15, RNF07, RNF08.
"""

from datetime import date, time
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.avaliacao.models import Avaliacao
from apps.cadastro.models import TipoUsuario, Usuario
from apps.cardapio.models import Campus, Refeicao, TipoRefeicao

pytestmark = pytest.mark.django_db

_contador = 0


def _proximo():
    global _contador
    _contador += 1
    return _contador


def criar_usuario():
    n = _proximo()
    return Usuario.objects.create_user(
        password="Senha-forte-123",
        tipo_usuario=TipoUsuario.ESTUDANTE,
        matricula_siape=f"{n:09d}",
        apelido=f"aval{n}",
        email_institucional=f"{n:09d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
    )


def criar_refeicao():
    n = _proximo()
    campus = Campus.objects.create(
        nome=f"Campus {n}",
        ru_latitude=Decimal("-15.763100"),
        ru_longitude=Decimal("-47.866900"),
        raio_confirmacao_metros=150,
        centro_latitude=Decimal("-15.765000"),
        centro_longitude=Decimal("-47.868000"),
        raio_deteccao_metros=1500,
    )
    return Refeicao.objects.create(
        campus=campus,
        data=date(2026, 11, 9),
        tipo=TipoRefeicao.ALMOCO,
        horario_inicio=time(11, 0),
        horario_fim=time(14, 0),
        fonte_pdf_url="https://ru.unb.br/cardapio.pdf",
    )


def criar_avaliacao(**kwargs):
    dados = {"nota": 4}
    dados.update(kwargs)
    dados.setdefault("usuario", criar_usuario())
    dados.setdefault("refeicao", criar_refeicao())
    return Avaliacao.objects.create(**dados)


def test_valores_padrao():
    av = criar_avaliacao()
    assert av.oculta is False
    assert av.comentario is None
    assert av.editada_em is None
    assert av.pontos_concedidos_em is None
    assert av.criada_em is not None


@pytest.mark.parametrize("nota", [1, 2, 3, 4, 5])
def test_aceita_notas_de_1_a_5(nota):
    assert criar_avaliacao(nota=nota).nota == nota


@pytest.mark.parametrize("nota", [0, 6, -1])
def test_rejeita_nota_fora_de_1_a_5(nota):
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_avaliacao(nota=nota)


def test_comentario_com_500_caracteres_e_aceito():
    assert len(criar_avaliacao(comentario="a" * 500).comentario) == 500


def test_comentario_com_501_caracteres_e_rejeitado():
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_avaliacao(comentario="a" * 501)


def test_comentario_conta_caracteres_e_nao_bytes():
    # 500 letras acentuadas ocupam mais de 500 bytes em UTF-8.
    assert criar_avaliacao(comentario="ç" * 500).pk


def test_uma_avaliacao_por_usuario_por_refeicao():
    av = criar_avaliacao()
    with pytest.raises(IntegrityError), transaction.atomic():
        Avaliacao.objects.create(usuario=av.usuario, refeicao=av.refeicao, nota=2)


def test_mesmo_usuario_avalia_refeicoes_diferentes():
    av = criar_avaliacao()
    outra = criar_refeicao()
    Avaliacao.objects.create(usuario=av.usuario, refeicao=outra, nota=3)
    assert Avaliacao.objects.filter(usuario=av.usuario).count() == 2


def test_usuarios_diferentes_avaliam_a_mesma_refeicao():
    av = criar_avaliacao()
    Avaliacao.objects.create(usuario=criar_usuario(), refeicao=av.refeicao, nota=1)
    assert Avaliacao.objects.filter(refeicao=av.refeicao).count() == 2


def test_excluir_usuario_mantem_a_avaliacao_com_usuario_nulo():
    av = criar_avaliacao()
    av.usuario.delete()
    av.refresh_from_db()
    assert av.usuario is None


def test_excluir_refeicao_apaga_as_avaliacoes():
    av = criar_avaliacao()
    av.refeicao.delete()
    assert not Avaliacao.objects.filter(pk=av.pk).exists()
