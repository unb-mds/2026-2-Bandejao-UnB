"""Testes dos models do app `fila` (BD-01): Checkin,
TentativaCheckin, PerguntaSaida e RespostaSaida."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.cadastro.models import TipoUsuario, Usuario
from apps.cardapio.models import Campus, TipoRefeicao
from apps.fila.models import (
    Checkin,
    EstadoPergunta,
    MotivoRejeicao,
    PerguntaSaida,
    RespostaSaida,
    RespostaSaidaOpcao,
    ResultadoTentativa,
    TentativaCheckin,
)

pytestmark = pytest.mark.django_db

DIA = date(2026, 11, 9)
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
        apelido=f"fila{n}",
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


def criar_checkin(**kwargs):
    dados = {
        "tipo_refeicao": TipoRefeicao.ALMOCO,
        "data": DIA,
        "faixa_inicio": time(12, 0),
    }
    dados.update(kwargs)
    dados.setdefault("usuario", criar_usuario())
    dados.setdefault("campus", criar_campus())
    return Checkin.objects.create(**dados)


def criar_pergunta(**kwargs):
    agora = timezone.now()
    dados = {
        "devida_em": agora + timedelta(minutes=15),
        "expira_em": agora + timedelta(minutes=60),
    }
    dados.update(kwargs)
    dados.setdefault("checkin", criar_checkin())
    return PerguntaSaida.objects.create(**dados)


class TestCheckin:
    def test_valores_padrao(self):
        c = criar_checkin()
        assert c.registrado_em is None
        assert c.tempo_espera_min is None
        assert c.pontos_concedidos_em is None

    def test_tempo_espera_guarda_uma_casa_decimal(self):
        c = criar_checkin(tempo_espera_min=Decimal("12.5"))
        c.refresh_from_db()
        assert c.tempo_espera_min == Decimal("12.5")

    def test_um_checkin_por_usuario_campus_tipo_data(self):
        c = criar_checkin()
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_checkin(usuario=c.usuario, campus=c.campus)

    def test_mesmo_usuario_em_outro_tipo_ou_dia_ou_campus(self):
        c = criar_checkin()
        criar_checkin(usuario=c.usuario, campus=c.campus, tipo_refeicao="jantar")
        criar_checkin(usuario=c.usuario, campus=c.campus, data=DIA + timedelta(1))
        criar_checkin(usuario=c.usuario)
        assert Checkin.objects.filter(usuario=c.usuario).count() == 4

    def test_usuario_nulo_nao_colide_no_unique(self):
        campus = criar_campus()
        criar_checkin(usuario=None, campus=campus)
        criar_checkin(usuario=None, campus=campus)
        assert Checkin.objects.filter(usuario__isnull=True).count() == 2

    def test_excluir_usuario_anula_o_vinculo(self):
        c = criar_checkin()
        c.usuario.delete()
        c.refresh_from_db()
        assert c.usuario is None

    def test_campus_com_checkin_nao_pode_ser_excluido(self):
        c = criar_checkin()
        with pytest.raises(ProtectedError):
            c.campus.delete()


class TestTentativaCheckin:
    def test_aceita_varias_tentativas_da_mesma_conta_na_mesma_refeicao(self):
        usuario, campus = criar_usuario(), criar_campus()
        for _ in range(3):
            TentativaCheckin.objects.create(
                usuario=usuario,
                campus=campus,
                tipo_refeicao=TipoRefeicao.ALMOCO,
                data=DIA,
                resultado=ResultadoTentativa.REJEITADO,
                motivo=MotivoRejeicao.FORA_DO_HORARIO,
            )
        assert TentativaCheckin.objects.count() == 3

    def test_confirmada_nao_tem_motivo_nem_hora_obrigatorios(self):
        t = TentativaCheckin.objects.create(
            usuario=None,
            campus=criar_campus(),
            tipo_refeicao=TipoRefeicao.CAFE,
            data=DIA,
            resultado=ResultadoTentativa.CONFIRMADO,
        )
        assert t.motivo is None
        assert t.data_hora is None

    def test_excluir_usuario_anula_o_vinculo(self):
        usuario = criar_usuario()
        t = TentativaCheckin.objects.create(
            usuario=usuario,
            campus=criar_campus(),
            tipo_refeicao=TipoRefeicao.JANTAR,
            data=DIA,
            resultado=ResultadoTentativa.CONFIRMADO,
        )
        usuario.delete()
        t.refresh_from_db()
        assert t.usuario is None

    def test_confirmada_com_motivo_e_rejeitada(self):
        usuario, campus = criar_usuario(), criar_campus()
        with pytest.raises(IntegrityError), transaction.atomic():
            TentativaCheckin.objects.create(
                usuario=usuario,
                campus=campus,
                tipo_refeicao=TipoRefeicao.ALMOCO,
                data=DIA,
                resultado=ResultadoTentativa.CONFIRMADO,
                motivo=MotivoRejeicao.FORA_DO_HORARIO,
            )

    @pytest.mark.parametrize("motivo", [None, "", "outro_motivo"])
    def test_rejeitada_sem_motivo_valido_e_rejeitada(self, motivo):
        usuario, campus = criar_usuario(), criar_campus()
        with pytest.raises(IntegrityError), transaction.atomic():
            TentativaCheckin.objects.create(
                usuario=usuario,
                campus=campus,
                tipo_refeicao=TipoRefeicao.ALMOCO,
                data=DIA,
                resultado=ResultadoTentativa.REJEITADO,
                motivo=motivo,
            )

    @pytest.mark.parametrize("motivo", MotivoRejeicao.values)
    def test_rejeitada_aceita_cada_motivo_do_n4(self, motivo):
        t = TentativaCheckin.objects.create(
            campus=criar_campus(),
            tipo_refeicao=TipoRefeicao.ALMOCO,
            data=DIA,
            resultado=ResultadoTentativa.REJEITADO,
            motivo=motivo,
        )
        assert t.pk

    def test_campus_com_tentativa_nao_pode_ser_excluido(self):
        campus = criar_campus()
        TentativaCheckin.objects.create(
            campus=campus,
            tipo_refeicao=TipoRefeicao.JANTAR,
            data=DIA,
            resultado=ResultadoTentativa.CONFIRMADO,
        )
        with pytest.raises(ProtectedError):
            campus.delete()


class TestPerguntaSaida:
    def test_valores_padrao(self):
        p = criar_pergunta()
        assert p.estado == EstadoPergunta.PENDENTE
        assert p.tentativa == 1
        assert p.pontos_concedidos_em is None

    def test_uma_pergunta_por_checkin(self):
        p = criar_pergunta()
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_pergunta(checkin=p.checkin)

    @pytest.mark.parametrize("tentativa", [1, 2])
    def test_aceita_tentativa_1_e_2(self, tentativa):
        assert criar_pergunta(tentativa=tentativa).tentativa == tentativa

    @pytest.mark.parametrize("tentativa", [0, 3])
    def test_tentativa_so_pode_ser_1_ou_2(self, tentativa):
        checkin = criar_checkin()
        with pytest.raises(IntegrityError), transaction.atomic():
            criar_pergunta(checkin=checkin, tentativa=tentativa)

    def test_excluir_checkin_apaga_a_pergunta(self):
        p = criar_pergunta()
        p.checkin.delete()
        assert not PerguntaSaida.objects.filter(pk=p.pk).exists()


class TestRespostaSaida:
    def _resposta(self, pergunta, tentativa=1, opcao=RespostaSaidaOpcao.AINDA_NA_FILA):
        return RespostaSaida.objects.create(
            pergunta=pergunta,
            tentativa=tentativa,
            resposta=opcao,
            respondida_em=timezone.now(),
        )

    def test_no_maximo_uma_resposta_por_tentativa(self):
        p = criar_pergunta()
        self._resposta(p, 1)
        with pytest.raises(IntegrityError), transaction.atomic():
            self._resposta(p, 1)

    def test_segunda_tentativa_e_permitida(self):
        p = criar_pergunta()
        self._resposta(p, 1)
        self._resposta(p, 2, RespostaSaidaOpcao.SAI_ATE_5_MIN)
        assert p.respostas.count() == 2

    @pytest.mark.parametrize("tentativa", [0, 3])
    def test_tentativa_da_resposta_so_pode_ser_1_ou_2(self, tentativa):
        pergunta = criar_pergunta()
        with pytest.raises(IntegrityError), transaction.atomic():
            self._resposta(pergunta, tentativa)

    def test_excluir_pergunta_apaga_as_respostas(self):
        p = criar_pergunta()
        r = self._resposta(p)
        p.delete()
        assert not RespostaSaida.objects.filter(pk=r.pk).exists()
