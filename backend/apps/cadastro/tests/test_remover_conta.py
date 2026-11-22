"""RemoverContaCommand: exclusão de conta (BD-12, #164).

RNF07.4, RNF08, Cadastro N4 (4d) e ADR 0004 revisada: excluir a conta apaga a
linha de `USUARIO` (não há mais o status `removido`). Na mesma transação:
os contadores da pontuação somem (a conta sai do ranking na hora), os
registros de fila perdem a conta e a hora exata, as sessões do Django são
encerradas e os tokens vão junto (CASCADE). As avaliações ficam, sem
`usuario_id`, e aparecem como "usuário removido". A mesma matrícula/SIAPE, o
mesmo e-mail e o mesmo apelido podem se cadastrar de novo.
"""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import DatabaseError
from django.test import Client
from django.utils import timezone

from apps.avaliacao.models import Avaliacao
from apps.cadastro.conta_repository import ContaRepository
from apps.cadastro.models import StatusUsuario, TipoToken, Token
from apps.cadastro.remover_conta_command import RemoverContaCommand
from apps.cadastro.sessoes_da_conta import SessoesDaConta
from apps.cardapio.models import Campus, Refeicao, TipoRefeicao
from apps.fila.models import Checkin, ResultadoTentativa, TentativaCheckin
from apps.gamificacao.models import PontosSemestreCampus, PontuacaoUsuario
from apps.gamificacao.pontuacao_service import PontuacaoService

Usuario = get_user_model()

pytestmark = pytest.mark.django_db

DIA = date(2026, 11, 20)


def criar_conta(numero, status=StatusUsuario.ATIVO):
    conta = Usuario.objects.create_user(
        matricula_siape=f"2024{numero:05d}",
        tipo_usuario="estudante",
        apelido=f"conta{numero}",
        email_institucional=f"2024{numero:05d}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
        status=status,
    )
    PontuacaoService().inicializar_conta(conta)
    return conta


@pytest.fixture
def conta():
    return criar_conta(1)


@pytest.fixture
def outra():
    return criar_conta(2)


@pytest.fixture
def campus():
    return Campus.objects.create(
        nome="Darcy Ribeiro",
        rotulo_pagina_ru="Darcy Ribeiro",
        prefixo_arquivo_pdf="Darcy Ribeiro",
        ru_latitude=Decimal("-15.764203"),
        ru_longitude=Decimal("-47.870251"),
        raio_confirmacao_metros=150,
        centro_latitude=Decimal("-15.765000"),
        centro_longitude=Decimal("-47.868000"),
        raio_deteccao_metros=150,
    )


@pytest.fixture
def refeicao(campus):
    return Refeicao.objects.create(
        campus=campus,
        data=DIA,
        tipo=TipoRefeicao.ALMOCO,
        horario_inicio=time(11, 0),
        horario_fim=time(14, 0),
        fonte_pdf_url="https://ru.unb.br/cardapio.pdf",
    )


def existe(conta):
    return Usuario.objects.filter(pk=conta.pk).exists()


def criar_checkin(conta, campus, dia=DIA):
    return Checkin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao="almoco",
        data=dia,
        registrado_em=datetime.combine(dia, time(11, 47), tzinfo=UTC),
        faixa_inicio=time(11, 45),
        tempo_espera_min=Decimal("6.5"),
        pontos_concedidos_em=datetime.combine(dia, time(11, 47), tzinfo=UTC),
    )


def criar_tentativa(conta, campus, dia=DIA):
    return TentativaCheckin.objects.create(
        usuario=conta,
        campus=campus,
        tipo_refeicao="almoco",
        data=dia,
        data_hora=datetime.combine(dia, time(11, 47), tzinfo=UTC),
        resultado=ResultadoTentativa.CONFIRMADO,
    )


def logar(conta):
    """Abre uma sessão do Django para a conta (um aparelho)."""
    cliente = Client()
    cliente.force_login(conta)
    return cliente


def donos_das_sessoes():
    """O `_auth_user_id` de cada sessão com login (as de visitante ficam de fora)."""
    donos = (
        sessao.get_decoded().get("_auth_user_id") for sessao in Session.objects.all()
    )
    return sorted(dono for dono in donos if dono)


# --- o status `removido` e `removido_em` saíram ----------------------------


def test_status_removido_nao_existe_mais():
    assert [s.value for s in StatusUsuario] == ["pendente", "ativo", "suspenso"]
    assert not hasattr(StatusUsuario, "REMOVIDO")


def test_usuario_nao_tem_mais_removido_em():
    assert "removido_em" not in {campo.name for campo in Usuario._meta.get_fields()}


@pytest.mark.parametrize(
    ("status", "ativa"),
    [
        (StatusUsuario.PENDENTE, True),
        (StatusUsuario.ATIVO, True),
        (StatusUsuario.SUSPENSO, False),
    ],
)
def test_so_a_conta_suspensa_nao_autentica(status, ativa):
    assert Usuario(status=status).is_active is ativa


# --- RemoverContaCommand: os efeitos ---------------------------------------


def test_apaga_a_linha_de_usuario(conta):
    assert RemoverContaCommand().executar(conta) is True

    assert not existe(conta)


@pytest.mark.parametrize(
    "status", [StatusUsuario.PENDENTE, StatusUsuario.ATIVO, StatusUsuario.SUSPENSO]
)
def test_remove_a_conta_em_qualquer_status(status):
    conta = criar_conta(7, status=status)

    RemoverContaCommand().executar(conta)

    assert not existe(conta)


def test_matricula_email_e_apelido_podem_se_cadastrar_de_novo(conta):
    dados = {
        "matricula_siape": conta.matricula_siape,
        "tipo_usuario": "estudante",
        "apelido": conta.apelido,
        "email_institucional": conta.email_institucional,
        "aceite_privacidade_em": timezone.now(),
        "versao_aviso_aceita": "teste",
        "password": "outra-senha-123",
    }

    RemoverContaCommand().executar(conta)
    novo = Usuario.objects.create_user(**dados)

    assert novo.pk != conta.pk
    assert Usuario.objects.filter(matricula_siape=dados["matricula_siape"]).count() == 1


def test_apaga_os_contadores_e_a_conta_sai_do_ranking_na_hora(conta, campus):
    PontuacaoUsuario.objects.filter(usuario=conta).update(
        pontos_totais=40, participa_ranking=True
    )
    PontosSemestreCampus.objects.create(
        usuario=conta, campus=campus, semestre_referencia="2026.2", pontos=40
    )

    RemoverContaCommand().executar(conta)

    assert not PontuacaoUsuario.objects.filter(usuario_id=conta.pk).exists()
    assert not PontosSemestreCampus.objects.filter(usuario_id=conta.pk).exists()


def test_registros_de_fila_de_qualquer_data_perdem_a_conta_e_a_hora(conta, campus):
    # A retenção de 4 semanas ainda não alcançaria um registro de ontem.
    recente = criar_checkin(conta, campus, DIA)
    tentativa = criar_tentativa(conta, campus, DIA)

    RemoverContaCommand().executar(conta)

    recente.refresh_from_db()
    tentativa.refresh_from_db()
    assert recente.usuario_id is None
    assert recente.registrado_em is None
    assert tentativa.usuario_id is None
    assert tentativa.data_hora is None
    # Fica o que a previsão de pico usa (RF13, RF22).
    assert recente.campus_id == campus.pk
    assert recente.data == DIA
    assert recente.tempo_espera_min == Decimal("6.5")


def test_encerra_as_sessoes_de_todos_os_aparelhos(conta, outra):
    for _ in range(3):
        logar(conta)
    logar(outra)
    assert donos_das_sessoes().count(str(conta.pk)) == 3

    RemoverContaCommand().executar(conta)

    assert donos_das_sessoes() == [str(outra.pk)]


def test_avaliacoes_ficam_sem_usuario(conta, outra, refeicao):
    avaliacao = Avaliacao.objects.create(
        usuario=conta, refeicao=refeicao, nota=4, comentario="Bom"
    )
    de_outra = Avaliacao.objects.create(usuario=outra, refeicao=refeicao, nota=2)

    RemoverContaCommand().executar(conta)

    avaliacao.refresh_from_db()
    de_outra.refresh_from_db()
    assert avaliacao.usuario_id is None
    assert (avaliacao.nota, avaliacao.comentario) == (4, "Bom")
    assert de_outra.usuario_id == outra.pk


def test_tokens_da_conta_vao_junto(conta, outra):
    for dona in (conta, outra):
        Token.objects.create(
            usuario=dona,
            tipo=TipoToken.CONFIRMACAO_EMAIL,
            token_hash=f"hash-{dona.pk}",
            expira_em=timezone.now() + timedelta(hours=24),
        )

    RemoverContaCommand().executar(conta)

    assert not Token.objects.filter(usuario_id=conta.pk).exists()
    assert Token.objects.filter(usuario_id=outra.pk).count() == 1


def test_nao_mexe_nas_outras_contas(conta, outra, campus):
    PontuacaoUsuario.objects.filter(usuario=outra).update(pontos_totais=15)
    checkin = criar_checkin(outra, campus)
    logar(outra)

    RemoverContaCommand().executar(conta)

    assert existe(outra)
    assert PontuacaoUsuario.objects.get(usuario=outra).pontos_totais == 15
    checkin.refresh_from_db()
    assert checkin.usuario_id == outra.pk
    assert checkin.registrado_em is not None
    assert donos_das_sessoes() == [str(outra.pk)]


def test_conta_ja_apagada_devolve_false_sem_erro(conta):
    RemoverContaCommand().executar(conta)

    assert RemoverContaCommand().executar(conta) is False


# --- tudo ou nada ----------------------------------------------------------


def estado_da_conta(conta):
    return (
        existe(conta),
        PontuacaoUsuario.objects.filter(usuario_id=conta.pk).exists(),
        Checkin.objects.filter(usuario_id=conta.pk).count(),
        TentativaCheckin.objects.filter(usuario_id=conta.pk).count(),
        donos_das_sessoes().count(str(conta.pk)),
    )


@pytest.mark.parametrize(
    "alvo",
    [
        "apps.gamificacao.pontuacao_service.PontuacaoService.apagar_contadores",
        "apps.fila.retencao_fila_service.RetencaoFilaService.desvincular_conta",
        "apps.cadastro.sessoes_da_conta.SessoesDaConta.encerrar_todas",
        "apps.cadastro.conta_repository.ContaRepository.excluir",
    ],
)
def test_falha_em_qualquer_passo_desfaz_todos(conta, campus, alvo):
    criar_checkin(conta, campus)
    criar_tentativa(conta, campus)
    logar(conta)
    antes = estado_da_conta(conta)
    assert antes == (True, True, 1, 1, 1)

    with (
        mock.patch(alvo, side_effect=DatabaseError("falha simulada")),
        pytest.raises(DatabaseError),
    ):
        RemoverContaCommand().executar(conta)

    assert estado_da_conta(conta) == antes
    # O vínculo e a hora também voltaram.
    assert Checkin.objects.get(usuario=conta).registrado_em is not None
    assert TentativaCheckin.objects.get(usuario=conta).data_hora is not None


# --- os colaboradores ------------------------------------------------------


def test_apagar_contadores_so_apaga_os_da_conta(conta, outra, campus):
    for dona in (conta, outra):
        PontosSemestreCampus.objects.create(
            usuario=dona, campus=campus, semestre_referencia="2026.2", pontos=10
        )

    PontuacaoService().apagar_contadores(conta)

    assert not PontuacaoUsuario.objects.filter(usuario=conta).exists()
    assert not PontosSemestreCampus.objects.filter(usuario=conta).exists()
    assert PontuacaoUsuario.objects.filter(usuario=outra).exists()
    assert PontosSemestreCampus.objects.filter(usuario=outra).count() == 1


def test_apagar_contadores_de_conta_sem_contador_nao_quebra(conta):
    PontuacaoUsuario.objects.filter(usuario=conta).delete()

    PontuacaoService().apagar_contadores(conta)


def test_encerrar_todas_apaga_tambem_a_sessao_expirada(conta, outra):
    logar(conta)
    logar(outra)
    Session.objects.filter(
        session_key__in=[
            s.session_key
            for s in Session.objects.all()
            if s.get_decoded().get("_auth_user_id") == str(conta.pk)
        ]
    ).update(expire_date=timezone.now() - timedelta(days=1))

    SessoesDaConta().encerrar_todas(conta)

    assert donos_das_sessoes() == [str(outra.pk)]


def test_encerrar_todas_ignora_sessao_de_visitante(conta):
    Client().get("/api/csrf/")  # sessão sem login, se o app criar alguma
    Session.objects.create(
        session_key="visitante",
        session_data="e30:1x:x",  # sessão com dados inválidos para decodificar
        expire_date=timezone.now() + timedelta(days=1),
    )
    logar(conta)

    SessoesDaConta().encerrar_todas(conta)

    assert Session.objects.filter(session_key="visitante").exists()
    assert str(conta.pk) not in donos_das_sessoes()


def test_excluir_do_repositorio_apaga_a_conta(conta):
    ContaRepository().excluir(conta)

    assert not existe(conta)
