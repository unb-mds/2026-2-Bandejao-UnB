"""Testes dos models do app `gamificacao` (BD-01):
PontuacaoUsuario e PontosSemestreCampus."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.cadastro.models import TipoUsuario, Usuario
from apps.cardapio.models import Campus
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario

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
        apelido=f"game{n}",
        email_institucional=f"{n:09d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
    )


def criar_campus():
    return Campus.objects.create(
        nome=f"Campus {_proximo()}",
        ru_latitude=Decimal("-15.763100"),
        ru_longitude=Decimal("-47.866900"),
        raio_confirmacao_metros=150,
        centro_latitude=Decimal("-15.765000"),
        centro_longitude=Decimal("-47.868000"),
        raio_deteccao_metros=1500,
    )


class TestPontuacaoUsuario:
    def test_valores_padrao(self):
        p = PontuacaoUsuario.objects.create(usuario=criar_usuario())
        assert p.pontos_totais == 0
        assert p.sequencia_atual == 0
        assert p.ultima_semana_completada is None
        assert p.participa_ranking is False
        assert p.atualizado_em is not None

    def test_uma_pontuacao_por_conta(self):
        usuario = criar_usuario()
        PontuacaoUsuario.objects.create(usuario=usuario)
        with pytest.raises(IntegrityError), transaction.atomic():
            PontuacaoUsuario.objects.create(usuario=usuario)

    def test_acessivel_pelo_usuario(self):
        usuario = criar_usuario()
        p = PontuacaoUsuario.objects.create(usuario=usuario)
        assert usuario.pontuacao == p

    def test_aceita_pontos_e_sequencia_zero(self):
        p = PontuacaoUsuario.objects.create(
            usuario=criar_usuario(), pontos_totais=0, sequencia_atual=0
        )
        assert p.pk

    def test_pontos_totais_negativos_sao_rejeitados(self):
        usuario = criar_usuario()
        with pytest.raises(IntegrityError), transaction.atomic():
            PontuacaoUsuario.objects.create(usuario=usuario, pontos_totais=-1)

    def test_sequencia_negativa_e_rejeitada(self):
        usuario = criar_usuario()
        with pytest.raises(IntegrityError), transaction.atomic():
            PontuacaoUsuario.objects.create(usuario=usuario, sequencia_atual=-1)

    def test_excluir_usuario_apaga_a_pontuacao(self):
        usuario = criar_usuario()
        p = PontuacaoUsuario.objects.create(usuario=usuario)
        usuario.delete()
        assert not PontuacaoUsuario.objects.filter(pk=p.pk).exists()


class TestPontosSemestreCampus:
    def _linha(self, **kwargs):
        dados = {"semestre_referencia": "2026.2", "pontos": 10}
        dados.update(kwargs)
        dados.setdefault("usuario", criar_usuario())
        dados.setdefault("campus", criar_campus())
        return PontosSemestreCampus.objects.create(**dados)

    def test_uma_linha_por_conta_campus_e_semestre(self):
        p = self._linha()
        with pytest.raises(IntegrityError), transaction.atomic():
            self._linha(usuario=p.usuario, campus=p.campus)  # só repete a chave

    def test_mesma_conta_em_outro_semestre_ou_campus(self):
        p = self._linha()
        self._linha(usuario=p.usuario, campus=p.campus, semestre_referencia="2027.1")
        self._linha(usuario=p.usuario)
        assert PontosSemestreCampus.objects.filter(usuario=p.usuario).count() == 3

    def test_aceita_pontos_zero(self):
        assert self._linha(pontos=0).pontos == 0

    def test_pontos_negativos_sao_rejeitados(self):
        usuario, campus = criar_usuario(), criar_campus()
        with pytest.raises(IntegrityError), transaction.atomic():
            self._linha(usuario=usuario, campus=campus, pontos=-1)

    def test_excluir_usuario_apaga_as_linhas(self):
        p = self._linha()
        p.usuario.delete()
        assert not PontosSemestreCampus.objects.filter(pk=p.pk).exists()

    def test_campus_com_pontos_nao_pode_ser_excluido(self):
        p = self._linha()
        with pytest.raises(ProtectedError):
            p.campus.delete()

    def test_atualizado_em_muda_a_cada_save(self):
        p = self._linha()
        antes = p.atualizado_em
        p.pontos = 20
        p.save()
        p.refresh_from_db()
        assert p.atualizado_em > antes
