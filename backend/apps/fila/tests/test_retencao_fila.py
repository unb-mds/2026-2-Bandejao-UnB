"""Retenção de 4 semanas dos registros de fila (BD-11, #163).

Fila N4 (4d) e RNF07.3: depois de 4 semanas, `Checkin` e `TentativaCheckin`
perdem a conta, `registrado_em` e `data_hora`. Campus, tipo, data, faixa e
tempo de espera ficam para a previsão de pico (RF13, RF22); o marcador de
pontos fica para a gamificação (ADR 0011). Os horários da pergunta e da
resposta de saída também ficam, sem conta. O mesmo serviço retira o vínculo
de uma conta excluída (`desvincular_conta`, que o `RemoverContaCommand` da
BD-12 vai chamar, RNF07.4).
"""

import logging
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import DatabaseError
from django.db.models import Avg, Count, QuerySet
from django.utils import timezone

from apps.fila.checkin_repository import CheckinRepository
from apps.fila.management.commands.desvincular_registros_fila import (
    DesvincularRegistrosFilaJob,
)
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
from apps.fila.retencao_fila_service import RetencaoFilaService

HOJE = date(2026, 11, 21)
# Data mais antiga que ainda fica ligada à conta: exatamente 4 semanas antes.
LIMITE = HOJE - timedelta(weeks=4)
CINCO_SEMANAS = HOJE - timedelta(weeks=5)


def momento(dia, hora=time(11, 47, 23)):
    return datetime.combine(dia, hora, tzinfo=UTC)


def criar_checkin(conta, campus, dia, tipo="almoco", faixa=time(11, 45), tempo=None):
    return Checkin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao=tipo,
        data=dia,
        registrado_em=momento(dia),
        faixa_inicio=faixa,
        tempo_espera_min=tempo,
        pontos_concedidos_em=momento(dia),
    )


def criar_tentativa(conta, campus, dia, rejeitada=False):
    return TentativaCheckin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao="almoco",
        data=dia,
        data_hora=momento(dia),
        resultado=(
            ResultadoTentativa.REJEITADO if rejeitada else ResultadoTentativa.CONFIRMADO
        ),
        motivo=MotivoRejeicao.FORA_DO_HORARIO if rejeitada else None,
    )


@pytest.fixture
def outra_conta(db):
    return get_user_model().objects.create_user(
        matricula_siape="202400003",
        tipo_usuario="estudante",
        apelido="edu",
        email_institucional="202400003@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )


def recarregar(*objetos):
    for objeto in objetos:
        objeto.refresh_from_db()


# --- desvincular_antigos ---------------------------------------------------


def test_registro_de_cinco_semanas_perde_o_vinculo_e_a_hora(conta, darcy):
    checkin = criar_checkin(conta, darcy, CINCO_SEMANAS, tempo=Decimal("7.5"))
    tentativa = criar_tentativa(conta, darcy, CINCO_SEMANAS)

    RetencaoFilaService().desvincular_antigos(HOJE)

    recarregar(checkin, tentativa)
    assert checkin.usuario_id is None
    assert checkin.registrado_em is None
    assert tentativa.usuario_id is None
    assert tentativa.data_hora is None


def test_retencao_mantem_os_campos_da_previsao_e_o_marcador_de_pontos(conta, darcy):
    checkin = criar_checkin(
        conta,
        darcy,
        CINCO_SEMANAS,
        tipo="jantar",
        faixa=time(18, 0),
        tempo=Decimal("7.5"),
    )
    tentativa = criar_tentativa(conta, darcy, CINCO_SEMANAS, rejeitada=True)

    RetencaoFilaService().desvincular_antigos(HOJE)

    recarregar(checkin, tentativa)
    assert checkin.campus_id == darcy.pk
    assert checkin.tipo_refeicao == "jantar"
    assert checkin.data == CINCO_SEMANAS
    assert checkin.faixa_inicio == time(18, 0)
    assert checkin.tempo_espera_min == Decimal("7.5")
    assert checkin.pontos_concedidos_em == momento(CINCO_SEMANAS)
    assert tentativa.campus_id == darcy.pk
    assert tentativa.data == CINCO_SEMANAS
    assert tentativa.resultado == ResultadoTentativa.REJEITADO
    assert tentativa.motivo == MotivoRejeicao.FORA_DO_HORARIO


@pytest.mark.parametrize(
    ("dia", "desvinculado"),
    [
        (LIMITE - timedelta(days=1), True),
        (LIMITE, False),
        (HOJE - timedelta(days=1), False),
        (HOJE, False),
    ],
)
def test_prazo_e_de_quatro_semanas_contadas_pela_data(conta, darcy, dia, desvinculado):
    """Só sai o que tem `data` anterior a 4 semanas; o próprio dia-limite fica."""
    checkin = criar_checkin(conta, darcy, dia)
    tentativa = criar_tentativa(conta, darcy, dia)

    RetencaoFilaService().desvincular_antigos(HOJE)

    recarregar(checkin, tentativa)
    assert (checkin.usuario_id is None) is desvinculado
    assert (checkin.registrado_em is None) is desvinculado
    assert (tentativa.usuario_id is None) is desvinculado
    assert (tentativa.data_hora is None) is desvinculado


def test_devolve_quantos_registros_foram_desvinculados(conta, darcy):
    criar_checkin(conta, darcy, CINCO_SEMANAS)
    criar_tentativa(conta, darcy, CINCO_SEMANAS)
    criar_tentativa(conta, darcy, CINCO_SEMANAS, rejeitada=True)
    criar_checkin(conta, darcy, HOJE)

    assert RetencaoFilaService().desvincular_antigos(HOJE) == 3


def test_rodar_de_novo_nao_conta_o_que_ja_foi_desvinculado(conta, darcy):
    criar_checkin(conta, darcy, CINCO_SEMANAS)
    criar_tentativa(conta, darcy, CINCO_SEMANAS)
    servico = RetencaoFilaService()

    servico.desvincular_antigos(HOJE)

    assert servico.desvincular_antigos(HOJE) == 0


def test_checkins_da_mesma_refeicao_de_contas_diferentes_ficam_sem_conta(
    conta, outra_conta, darcy
):
    """Com a conta nula, o UNIQUE (conta, campus, tipo, data) não restringe
    nada: NULL não colide no SQLite nem no MySQL, então a retenção não bate
    nele."""
    criar_checkin(conta, darcy, CINCO_SEMANAS)
    criar_checkin(outra_conta, darcy, CINCO_SEMANAS)

    assert RetencaoFilaService().desvincular_antigos(HOJE) == 2
    assert Checkin.objects.filter(usuario__isnull=True).count() == 2


def test_previsao_continua_igual_depois_da_retencao(conta, outra_conta, darcy, gama):
    """A previsão (RF13, Fila N4 4c) conta check-ins por campus, tipo, data e
    faixa, e a espera estimada (RF22) usa o tempo de espera. A agregação
    tem que dar o mesmo resultado antes e depois."""
    for dia in (CINCO_SEMANAS, LIMITE - timedelta(days=1), LIMITE, HOJE):
        criar_checkin(conta, darcy, dia, faixa=time(11, 30), tempo=Decimal("4.0"))
        criar_checkin(
            outra_conta, darcy, dia, faixa=time(11, 45), tempo=Decimal("12.5")
        )
        criar_checkin(conta, gama, dia, tipo="jantar", faixa=time(18, 15))

    def agregado():
        return list(
            Checkin.objects.values("campus", "tipo_refeicao", "data", "faixa_inicio")
            .annotate(total=Count("id"), espera=Avg("tempo_espera_min"))
            .order_by("campus", "tipo_refeicao", "data", "faixa_inicio")
        )

    antes = agregado()

    assert RetencaoFilaService().desvincular_antigos(HOJE) == 6
    assert agregado() == antes


def test_resposta_de_saida_perde_o_vinculo_junto_com_o_checkin(conta, darcy):
    """`RespostaSaida` não guarda a conta: chega a ela pela pergunta e pelo
    check-in (Fila N4 4b)."""
    checkin = criar_checkin(conta, darcy, CINCO_SEMANAS)
    pergunta = PerguntaSaida.objects.create(
        checkin=checkin,
        estado=EstadoPergunta.RESPONDIDA,
        devida_em=momento(CINCO_SEMANAS),
        expira_em=momento(CINCO_SEMANAS),
    )
    RespostaSaida.objects.create(
        pergunta=pergunta,
        tentativa=1,
        resposta=RespostaSaidaOpcao.SAI_ATE_5_MIN,
        respondida_em=momento(CINCO_SEMANAS),
    )

    RetencaoFilaService().desvincular_antigos(HOJE)

    assert RespostaSaida.objects.count() == 1
    assert not RespostaSaida.objects.filter(pergunta__checkin__usuario=conta).exists()
    # A pergunta continua, ligada ao mesmo check-in (agora sem conta).
    pergunta.refresh_from_db()
    assert pergunta.checkin_id == checkin.pk
    assert pergunta.checkin.usuario_id is None


@pytest.mark.parametrize("modelo", [Checkin, TentativaCheckin])
def test_registro_sem_conta_mas_com_hora_tambem_perde_a_hora(conta, darcy, modelo):
    """Conta apagada sem passar pelo `desvincular_conta` (pelo admin, por
    exemplo): o `SET_NULL` anula a conta e deixa a hora. A retenção apaga a
    hora mesmo assim."""
    criar = criar_checkin if modelo is Checkin else criar_tentativa
    registro = criar(conta, darcy, CINCO_SEMANAS)
    modelo.objects.filter(pk=registro.pk).update(usuario=None)

    assert RetencaoFilaService().desvincular_antigos(HOJE) == 1

    recarregar(registro)
    assert registro.usuario_id is None
    hora = "registrado_em" if modelo is Checkin else "data_hora"
    assert getattr(registro, hora) is None


@pytest.mark.parametrize("modelo", [Checkin, TentativaCheckin])
def test_registro_com_conta_e_sem_hora_tambem_perde_a_conta(conta, darcy, modelo):
    criar = criar_checkin if modelo is Checkin else criar_tentativa
    registro = criar(conta, darcy, CINCO_SEMANAS)
    hora = "registrado_em" if modelo is Checkin else "data_hora"
    modelo.objects.filter(pk=registro.pk).update(**{hora: None})

    assert RetencaoFilaService().desvincular_antigos(HOJE) == 1

    recarregar(registro)
    assert registro.usuario_id is None


def test_horarios_da_pergunta_e_do_marcador_ficam(conta, darcy):
    """O que a retenção anula é só a conta, `registrado_em` e `data_hora`.
    `pontos_concedidos_em` (gamificação, ADR 0011) e os horários da pergunta
    e da resposta de saída ficam, sem conta (decisão registrada no C4 4d)."""
    checkin = criar_checkin(conta, darcy, CINCO_SEMANAS)
    pergunta = PerguntaSaida.objects.create(
        checkin=checkin,
        devida_em=momento(CINCO_SEMANAS),
        expira_em=momento(CINCO_SEMANAS),
    )

    RetencaoFilaService().desvincular_antigos(HOJE)

    recarregar(checkin, pergunta)
    assert checkin.pontos_concedidos_em == momento(CINCO_SEMANAS)
    assert pergunta.devida_em == momento(CINCO_SEMANAS)
    assert pergunta.expira_em == momento(CINCO_SEMANAS)


def test_falha_numa_tabela_desfaz_a_outra(conta, darcy):
    """As duas tabelas mudam na mesma transação: se o UPDATE da tentativa
    falhar, o check-in continua com a conta."""
    checkin = criar_checkin(conta, darcy, CINCO_SEMANAS)
    criar_tentativa(conta, darcy, CINCO_SEMANAS)
    update_original = QuerySet.update

    def update_que_falha_na_tentativa(self, **campos):
        if self.model is TentativaCheckin:
            raise DatabaseError("falha simulada")
        return update_original(self, **campos)

    with (
        mock.patch.object(QuerySet, "update", update_que_falha_na_tentativa),
        pytest.raises(DatabaseError),
    ):
        RetencaoFilaService().desvincular_antigos(HOJE)

    recarregar(checkin)
    assert checkin.usuario_id == conta.pk
    assert checkin.registrado_em is not None


def test_prazo_vem_do_anexo_a(conta, darcy):
    """O prazo é o `retencao_semanas` da `ParametrosFilaConfig`, e não um
    número fixo no serviço."""
    dia = HOJE - timedelta(weeks=2)
    checkin = criar_checkin(conta, darcy, dia)

    with mock.patch(
        "apps.fila.retencao_fila_service.ParametrosFilaConfig.retencao_semanas", 1
    ):
        RetencaoFilaService().desvincular_antigos(HOJE)

    recarregar(checkin)
    assert checkin.usuario_id is None


# --- desvincular_conta -----------------------------------------------------


def test_desvincular_conta_retira_todos_os_registros_da_conta(
    conta, outra_conta, darcy
):
    """Na exclusão de conta (RNF07.4), até o check-in de hoje sai da conta."""
    da_conta = [
        criar_checkin(conta, darcy, HOJE),
        criar_checkin(conta, darcy, CINCO_SEMANAS),
    ]
    tentativa = criar_tentativa(conta, darcy, HOJE)
    de_outra = criar_checkin(outra_conta, darcy, HOJE)
    tentativa_de_outra = criar_tentativa(outra_conta, darcy, HOJE)

    assert RetencaoFilaService().desvincular_conta(conta) == 3

    recarregar(*da_conta, tentativa, de_outra, tentativa_de_outra)
    for checkin in da_conta:
        assert checkin.usuario_id is None
        assert checkin.registrado_em is None
    assert tentativa.usuario_id is None
    assert tentativa.data_hora is None
    assert de_outra.usuario_id == outra_conta.pk
    assert de_outra.registrado_em is not None
    assert tentativa_de_outra.usuario_id == outra_conta.pk
    assert tentativa_de_outra.data_hora is not None


def test_desvincular_conta_mantem_os_registros_para_a_previsao(conta, darcy):
    checkin = criar_checkin(conta, darcy, HOJE, tempo=Decimal("3.0"))

    RetencaoFilaService().desvincular_conta(conta)

    recarregar(checkin)
    assert Checkin.objects.count() == 1
    assert checkin.faixa_inicio == time(11, 45)
    assert checkin.tempo_espera_min == Decimal("3.0")


def test_desvincular_conta_sem_registros_nao_falha(conta):
    assert RetencaoFilaService().desvincular_conta(conta) == 0


# --- repositório -----------------------------------------------------------


def test_repositorio_desvincula_so_antes_da_data_pedida(conta, darcy):
    antigo = criar_checkin(conta, darcy, LIMITE - timedelta(days=1))
    no_limite = criar_checkin(conta, darcy, LIMITE)

    assert CheckinRepository().desvincular_antes_de(LIMITE) == 1

    recarregar(antigo, no_limite)
    assert antigo.usuario_id is None
    assert no_limite.usuario_id == conta.pk


# --- DesvincularRegistrosFilaJob -------------------------------------------


def test_job_usa_o_dia_de_brasilia(conta, darcy):
    """21/11 às 01h UTC ainda é 20/11 em Brasília: com o dia de Brasília, o
    check-in de 23/10 está exatamente no limite de 4 semanas e fica."""
    checkin = criar_checkin(conta, darcy, date(2026, 10, 23))

    with mock.patch(
        "django.utils.timezone.now",
        return_value=datetime(2026, 11, 21, 1, 0, tzinfo=UTC),
    ):
        assert DesvincularRegistrosFilaJob().executar() == 0

    recarregar(checkin)
    assert checkin.usuario_id == conta.pk


def test_job_desvincula_o_dia_anterior_ao_limite_de_brasilia(conta, darcy):
    """No mesmo instante, o check-in de 22/10 (um dia antes do limite de
    Brasília) sai. Pega um erro de um dia para trás no limite."""
    checkin = criar_checkin(conta, darcy, date(2026, 10, 22))

    with mock.patch(
        "django.utils.timezone.now",
        return_value=datetime(2026, 11, 21, 1, 0, tzinfo=UTC),
    ):
        assert DesvincularRegistrosFilaJob().executar() == 1

    recarregar(checkin)
    assert checkin.usuario_id is None


def test_falha_do_job_vai_para_o_log_e_e_propagada(caplog):
    """O erro sai no formato de log do projeto e o comando termina com erro
    (o cron da BD-07 guarda o status)."""

    class ServicoQueFalha:
        def desvincular_antigos(self, hoje):
            raise DatabaseError("falha simulada")

    with (
        caplog.at_level(logging.ERROR, logger="apps"),
        pytest.raises(DatabaseError),
    ):
        DesvincularRegistrosFilaJob(servico=ServicoQueFalha()).executar()

    assert "Falha na retenção dos registros de fila" in caplog.text


def test_comando_desvincula_e_escreve_so_a_contagem(conta, darcy, caplog):
    criar_checkin(conta, darcy, CINCO_SEMANAS)
    criar_tentativa(conta, darcy, CINCO_SEMANAS)
    saida = StringIO()

    with (
        mock.patch(
            "django.utils.timezone.now", return_value=momento(HOJE, time(12, 0))
        ),
        caplog.at_level(logging.INFO, logger="apps"),
    ):
        call_command("desvincular_registros_fila", stdout=saida)

    assert saida.getvalue().strip() == "Registros de fila desvinculados: 2"
    assert not Checkin.objects.filter(usuario__isnull=False).exists()
    # O log não leva dado da conta (RNF07).
    assert "Registros de fila desvinculados: 2" in caplog.text
    assert conta.matricula_siape not in caplog.text
    assert conta.email_institucional not in caplog.text
