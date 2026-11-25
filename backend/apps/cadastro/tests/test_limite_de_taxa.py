"""Limite de taxa no cadastro, no reenvio e no login (#123).

Pense no limite como a catraca do RU: cada IP tem um contador por rota, e
quem passa da conta na janela de 1 hora espera do lado de fora (429
`limite_excedido`, com `Retry-After`). No reenvio há ainda uma segunda
catraca, por conta, que é silenciosa: a resposta continua 200 (RF02.2), só
o e-mail deixa de sair.

Cada teste troca o limite por um número pequeno com `monkeypatch`, para não
fazer 60 pedidos. O relógio é o `django.utils.timezone.now` (mesmo mock do
`test_sessao_endpoint.py`): o throttle e o cache em banco leem dele.
"""

import logging
from datetime import UTC, datetime, timedelta
from smtplib import SMTPException
from unittest import mock

import pytest
from django.conf import settings as settings_do_django
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cadastro.models import StatusUsuario
from config.parametros import LimiteDeTaxaConfig

ROTA_CADASTRO = "/api/cadastro/"
ROTA_REENVIO = "/api/reenviar-confirmacao/"
ROTA_SESSAO = "/api/sessao/"

# (rota, atributo do LimiteDeTaxaConfig). Corpo vazio: a view responde 422,
# que também gasta o limite (o DRF conta antes de a view rodar).
ROTAS = [
    (ROTA_CADASTRO, "cadastro_por_ip"),
    (ROTA_REENVIO, "reenvio_por_ip"),
    (ROTA_SESSAO, "login_por_ip"),
]

AGORA = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
DEPOIS_DA_JANELA = AGORA + timedelta(hours=1, seconds=1)

IP_A = "200.130.1.10"
IP_B = "200.130.1.20"


@pytest.fixture(autouse=True)
def atras_do_proxy(settings):
    """O valor do CI (sem DEBUG), independente do .env de quem roda (guia 9.2)."""
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}


@pytest.fixture
def relogio():
    with mock.patch("django.utils.timezone.now", return_value=AGORA) as agora:
        yield agora


@pytest.fixture
def limite(monkeypatch):
    """Troca um limite do LimiteDeTaxaConfig: `limite("login_por_ip", "3/hour")`."""

    def trocar(nome, valor="3/hour"):
        monkeypatch.setattr(LimiteDeTaxaConfig, nome, valor)

    return trocar


def novo_cliente():
    """Cliente que exige CSRF, como o navegador (#112)."""
    cliente = APIClient(enforce_csrf_checks=True)
    resposta = cliente.get("/api/csrf/")
    cliente.credentials(HTTP_X_CSRFTOKEN=resposta.cookies["csrftoken"].value)
    return cliente


@pytest.fixture
def cliente(db):
    return novo_cliente()


def pedir(cliente, rota, ip=IP_A, corpo=None, encaminhado_por=None):
    """POST como o Caddy entrega: o IP do cliente é o último do X-Forwarded-For.

    `encaminhado_por` é o que o próprio cliente pôs no cabeçalho (forjado); o
    Caddy acrescenta o IP real no fim.
    """
    cabecalho = f"{encaminhado_por}, {ip}" if encaminhado_por else ip
    return cliente.post(
        rota, corpo or {}, format="json", HTTP_X_FORWARDED_FOR=cabecalho
    )


def assert_limite_excedido(resposta):
    assert resposta.status_code == 429
    corpo = resposta.json()
    assert set(corpo) == {"codigo", "mensagem"}
    assert corpo["codigo"] == "limite_excedido"
    assert corpo["mensagem"]
    assert int(resposta["Retry-After"]) > 0


def criar_conta(status=StatusUsuario.PENDENTE, matricula="202400001"):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        matricula_siape=matricula,
        tipo_usuario="estudante",
        apelido=f"conta{matricula[-3:]}",
        email_institucional=f"{matricula}@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
        status=status,
        email_confirmado=status != StatusUsuario.PENDENTE,
    )


# --- Por IP (cadastro, reenvio e login) ----------------------------------------


@pytest.mark.parametrize(("rota", "nome"), ROTAS)
def test_quarto_pedido_do_mesmo_ip_da_429_limite_excedido(
    cliente, limite, relogio, rota, nome
):
    limite(nome)
    for _ in range(3):
        assert pedir(cliente, rota).status_code != 429

    assert_limite_excedido(pedir(cliente, rota))


@pytest.mark.parametrize(("rota", "nome"), ROTAS)
def test_retry_after_diz_quanto_falta_para_a_janela_abrir(
    cliente, limite, relogio, rota, nome
):
    limite(nome)
    for _ in range(3):
        pedir(cliente, rota)
    relogio.return_value = AGORA + timedelta(minutes=20)

    resposta = pedir(cliente, rota)

    assert_limite_excedido(resposta)
    # O primeiro pedido sai da janela daqui a 40 minutos.
    assert int(resposta["Retry-After"]) == 40 * 60


@pytest.mark.parametrize(("rota", "nome"), ROTAS)
def test_depois_da_janela_o_pedido_passa_de_novo(cliente, limite, relogio, rota, nome):
    limite(nome)
    for _ in range(3):
        pedir(cliente, rota)
    assert_limite_excedido(pedir(cliente, rota))

    relogio.return_value = DEPOIS_DA_JANELA

    assert pedir(cliente, rota).status_code != 429


@pytest.mark.parametrize(("rota", "nome"), ROTAS)
def test_no_meio_da_janela_o_limite_continua_valendo(
    cliente, limite, relogio, rota, nome
):
    """Pega uma janela que encolheu (ex.: 300 s do tempo padrão do cache)."""
    limite(nome)
    for _ in range(3):
        pedir(cliente, rota)

    relogio.return_value = AGORA + timedelta(minutes=59)

    assert_limite_excedido(pedir(cliente, rota))


@pytest.mark.parametrize(("rota", "nome"), ROTAS)
def test_ips_diferentes_tem_contadores_separados(cliente, limite, relogio, rota, nome):
    limite(nome)
    for _ in range(3):
        pedir(cliente, rota, ip=IP_A)
    assert_limite_excedido(pedir(cliente, rota, ip=IP_A))

    assert pedir(cliente, rota, ip=IP_B).status_code != 429


def test_as_rotas_nao_dividem_o_contador(cliente, limite, relogio):
    for _, nome in ROTAS:
        limite(nome)
    for _ in range(3):
        pedir(cliente, ROTA_CADASTRO)
    assert_limite_excedido(pedir(cliente, ROTA_CADASTRO))

    assert pedir(cliente, ROTA_SESSAO).status_code != 429
    assert pedir(cliente, ROTA_REENVIO).status_code != 429


def test_pedido_recusado_pelo_csrf_nao_gasta_o_limite(limite, relogio, db):
    """O DRF checa as permissões antes do limite: o 403 não conta (guia 6.2)."""
    limite("login_por_ip")
    sem_token = APIClient(enforce_csrf_checks=True)
    for _ in range(5):
        resposta = sem_token.post(
            ROTA_SESSAO, {}, format="json", HTTP_X_FORWARDED_FOR=IP_A
        )
        assert resposta.status_code == 403

    assert pedir(novo_cliente(), ROTA_SESSAO).status_code != 429


def test_quem_ja_tem_sessao_tambem_tem_limite(usuario, limite, relogio):
    """Por isso não é o AnonRateThrottle, que ignora quem está logado (guia 6.2)."""
    limite("cadastro_por_ip")
    cliente = novo_cliente()
    cliente.force_login(usuario)
    cliente.credentials(HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
    for _ in range(3):
        pedir(cliente, ROTA_CADASTRO)

    assert_limite_excedido(pedir(cliente, ROTA_CADASTRO))


def test_o_ip_nao_fica_em_claro_na_chave_do_cache(cliente, limite, relogio):
    from django.db import connection

    limite("login_por_ip")
    pedir(cliente, ROTA_SESSAO)

    with connection.cursor() as cursor:
        cursor.execute("SELECT cache_key FROM cache_bandejao")
        chaves = [linha[0] for linha in cursor.fetchall()]
    assert chaves
    assert not any(IP_A in chave for chave in chaves)


def test_ipv6_da_mesma_faixa_64_divide_o_contador(cliente, limite, relogio):
    """Trocar o fim do endereço IPv6 não dá um contador novo (guia 9.5)."""
    limite("login_por_ip")
    for ip in (
        "2804:14c:5b:1::1",
        "2804:14c:5b:1::2",
        "2804:14c:5b:1:abcd:ef01:2345:6789",
    ):
        pedir(cliente, ROTA_SESSAO, ip=ip)

    assert_limite_excedido(pedir(cliente, ROTA_SESSAO, ip="2804:14c:5b:1::ffff"))


def test_ipv6_de_faixas_64_diferentes_tem_contadores_separados(
    cliente, limite, relogio
):
    limite("login_por_ip")
    for _ in range(3):
        pedir(cliente, ROTA_SESSAO, ip="2804:14c:5b:1::1")
    assert_limite_excedido(pedir(cliente, ROTA_SESSAO, ip="2804:14c:5b:1::1"))

    assert pedir(cliente, ROTA_SESSAO, ip="2804:14c:5b:2::1").status_code != 429


def test_ipv4_dentro_do_ipv6_conta_como_o_ipv4(cliente, limite, relogio):
    """`::ffff:1.2.3.4` é o IPv4 1.2.3.4, e não a faixa /64 de todo o IPv4."""
    limite("login_por_ip")
    for _ in range(3):
        pedir(cliente, ROTA_SESSAO, ip="::ffff:200.130.1.10")
    assert_limite_excedido(pedir(cliente, ROTA_SESSAO, ip=IP_A))

    assert pedir(cliente, ROTA_SESSAO, ip="::ffff:200.130.1.11").status_code != 429


def test_valor_que_nao_e_ip_tambem_tem_limite(cliente, limite, relogio):
    """Um cabeçalho estranho não quebra a rota nem escapa do limite."""
    limite("login_por_ip")
    for _ in range(3):
        pedir(cliente, ROTA_SESSAO, ip="desconhecido")

    assert_limite_excedido(pedir(cliente, ROTA_SESSAO, ip="desconhecido"))


def test_falha_ao_gravar_o_contador_do_ip_vai_para_o_log(
    cliente, limite, relogio, caplog
):
    """O DatabaseCache engole o DatabaseError: sem log, o limite estaria
    desligado em silêncio."""
    limite("login_por_ip")
    with (
        # Como o DatabaseCache faz com um DatabaseError: não grava e devolve
        # None (o set não repassa o False do _base_set).
        mock.patch(
            "django.core.cache.backends.db.DatabaseCache.set", return_value=None
        ),
        caplog.at_level(logging.ERROR, logger="apps.cadastro.limite_de_taxa"),
    ):
        resposta = pedir(cliente, ROTA_SESSAO)

    # O pedido segue (o limite não pode derrubar o login), mas fica no log.
    assert resposta.status_code != 429
    erros = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(erros) == 1
    assert "login_por_ip" in erros[0].getMessage()
    assert IP_A not in erros[0].getMessage()


def test_falha_na_segunda_gravacao_do_ip_tambem_vai_para_o_log(
    cliente, limite, relogio, caplog
):
    """A linha antiga continua na tabela: conferir só se a chave existe deixaria
    o contador congelado em silêncio a partir do 2º pedido."""
    limite("login_por_ip")
    pedir(cliente, ROTA_SESSAO)
    relogio.return_value = AGORA + timedelta(seconds=5)

    with (
        mock.patch(
            "django.core.cache.backends.db.DatabaseCache.set", return_value=None
        ),
        caplog.at_level(logging.ERROR, logger="apps.cadastro.limite_de_taxa"),
    ):
        pedir(cliente, ROTA_SESSAO)

    erros = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert len(erros) == 1
    assert "login_por_ip" in erros[0]


def test_gravar_aceita_o_horario_de_um_pedido_simultaneo():
    """Dois pedidos no mesmo instante gravam listas quase iguais (guia 9.6):
    a do outro, lida de volta, não é falha. Uma lista velha é."""
    from apps.cadastro.limite_de_taxa import gravar

    cache_falso = mock.Mock()
    agora = AGORA.timestamp()

    cache_falso.get.return_value = [agora - 0.5]
    assert gravar(cache_falso, "chave", [agora], 3600) is True

    cache_falso.get.return_value = [agora - 5, agora - 60]
    assert gravar(cache_falso, "chave", [agora, agora - 5], 3600) is False

    cache_falso.get.return_value = None
    assert gravar(cache_falso, "chave", [agora], 3600) is False


@pytest.mark.parametrize(("rota", "nome"), ROTAS)
def test_pedido_normal_nao_gera_log_de_erro_do_limite(
    cliente, limite, relogio, caplog, rota, nome
):
    """O `set` do DatabaseCache devolve None até quando grava: conferir o retorno
    dele daria um falso alarme a cada pedido."""
    limite(nome)
    criar_conta()
    with caplog.at_level(logging.WARNING, logger="apps.cadastro.limite_de_taxa"):
        pedir(cliente, rota, corpo={"emailInstitucional": "202400001@aluno.unb.br"})

    assert caplog.records == []


# --- IP atrás do proxy (Caddy) ---------------------------------------------------


def test_x_forwarded_for_forjado_pelo_cliente_nao_escapa_do_limite(
    cliente, limite, relogio
):
    """Só o último endereço (o que o Caddy acrescentou) identifica o cliente."""
    limite("login_por_ip")
    for forjado in ("9.9.9.9", "8.8.8.8", "7.7.7.7"):
        pedir(cliente, ROTA_SESSAO, ip=IP_A, encaminhado_por=forjado)

    assert_limite_excedido(
        pedir(cliente, ROTA_SESSAO, ip=IP_A, encaminhado_por="6.6.6.6")
    )


def test_sem_proxy_o_x_forwarded_for_e_ignorado(cliente, limite, relogio, settings):
    """No runserver (NUM_PROXIES = 0) vale o REMOTE_ADDR, mesmo com o cabeçalho."""
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 0}
    limite("login_por_ip")
    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        pedir(cliente, ROTA_SESSAO, ip=ip)

    # Outro X-Forwarded-For, mas o mesmo REMOTE_ADDR (127.0.0.1) do APIClient.
    assert_limite_excedido(pedir(cliente, ROTA_SESSAO, ip="4.4.4.4"))


@pytest.mark.parametrize(("atras_de_proxy", "esperado"), [("True", 1), ("False", 0)])
def test_num_proxies_segue_o_atras_de_proxy_https(
    carregar_settings, atras_de_proxy, esperado
):
    modulo = carregar_settings(ATRAS_DE_PROXY_HTTPS=atras_de_proxy)

    assert modulo.REST_FRAMEWORK["NUM_PROXIES"] == esperado


def test_num_proxies_padrao_em_producao_e_1(carregar_settings):
    """Sem DEBUG e sem a variável no .env: atrás do Caddy (ADR 0012)."""
    assert carregar_settings().REST_FRAMEWORK["NUM_PROXIES"] == 1


# --- Login: só o POST tem limite ---------------------------------------------------


@pytest.mark.parametrize("metodo", ["get", "delete"])
def test_get_e_delete_da_sessao_nao_tem_limite(cliente, limite, relogio, metodo):
    limite("login_por_ip")
    for _ in range(3):
        pedir(cliente, ROTA_SESSAO)
    assert_limite_excedido(pedir(cliente, ROTA_SESSAO))

    for _ in range(5):
        resposta = getattr(cliente, metodo)(ROTA_SESSAO, HTTP_X_FORWARDED_FOR=IP_A)
        assert resposta.status_code == 401


def test_login_bloqueado_da_conta_continua_com_o_proprio_codigo(cliente, relogio, db):
    """Com os números do LimiteDeTaxaConfig, o bloqueio por conta chega antes."""
    criar_conta(status=StatusUsuario.ATIVO)
    for _ in range(4):
        pedir(
            cliente,
            ROTA_SESSAO,
            corpo={
                "emailInstitucional": "202400001@aluno.unb.br",
                "senha": "senha-errada",
            },
        )

    resposta = pedir(
        cliente,
        ROTA_SESSAO,
        corpo={"emailInstitucional": "202400001@aluno.unb.br", "senha": "senha-errada"},
    )

    assert resposta.status_code == 429
    assert resposta.json()["codigo"] == "login_bloqueado"


# --- Reenvio: limite por conta, silencioso ----------------------------------------


def test_reenvio_acima_do_limite_da_conta_responde_200_sem_email(
    cliente, limite, relogio
):
    """5 IPs diferentes, a mesma conta: 5 respostas 200, só 3 e-mails."""
    limite("reenvio_por_conta")
    conta = criar_conta()

    respostas = [
        pedir(
            cliente,
            ROTA_REENVIO,
            ip=f"200.130.2.{final}",
            corpo={"emailInstitucional": "202400001@aluno.unb.br"},
        )
        for final in range(5)
    ]

    assert [r.status_code for r in respostas] == [200] * 5
    assert len({r.content for r in respostas}) == 1
    assert len(mail.outbox) == 3
    assert all(m.to == [conta.email_institucional] for m in mail.outbox)


def test_aviso_do_log_tem_o_id_da_conta_e_nao_tem_dado_pessoal(
    cliente, limite, relogio, caplog
):
    limite("reenvio_por_conta", "1/hour")
    conta = criar_conta()
    pedir(cliente, ROTA_REENVIO, corpo={"emailInstitucional": "202400001@aluno.unb.br"})

    with caplog.at_level(logging.WARNING, logger="apps.cadastro.limite_de_taxa"):
        pedir(
            cliente,
            ROTA_REENVIO,
            ip=IP_B,
            corpo={"emailInstitucional": "202400001@aluno.unb.br"},
        )

    mensagens = [r.getMessage() for r in caplog.records]
    assert any(str(conta.pk) in m for m in mensagens)
    assert not any("202400001" in m for m in mensagens)
    assert not any(conta.email_institucional in m for m in mensagens)


def test_depois_da_janela_a_conta_volta_a_receber_o_link(cliente, limite, relogio):
    limite("reenvio_por_conta", "1/hour")
    criar_conta()
    pedir(cliente, ROTA_REENVIO, corpo={"emailInstitucional": "202400001@aluno.unb.br"})
    pedir(
        cliente,
        ROTA_REENVIO,
        ip=IP_B,
        corpo={"emailInstitucional": "202400001@aluno.unb.br"},
    )
    assert len(mail.outbox) == 1

    relogio.return_value = DEPOIS_DA_JANELA
    pedir(cliente, ROTA_REENVIO, corpo={"emailInstitucional": "202400001@aluno.unb.br"})

    assert len(mail.outbox) == 2


def test_no_meio_da_janela_a_conta_continua_sem_link(cliente, limite, relogio):
    """Com `cache.incr`, a janela de 1 hora viraria 5 minutos, e isto falharia."""
    limite("reenvio_por_conta", "1/hour")
    criar_conta()
    pedir(cliente, ROTA_REENVIO, corpo={"emailInstitucional": "202400001@aluno.unb.br"})

    relogio.return_value = AGORA + timedelta(minutes=10)
    pedir(
        cliente,
        ROTA_REENVIO,
        ip=IP_B,
        corpo={"emailInstitucional": "202400001@aluno.unb.br"},
    )

    assert len(mail.outbox) == 1


def test_falha_no_smtp_nao_gasta_a_vaga_do_reenvio(cliente, limite, relogio):
    """Brevo fora do ar: a pessoa tenta 3 vezes e, quando ele volta, recebe o link."""
    limite("reenvio_por_conta")
    criar_conta()
    with mock.patch(
        "apps.cadastro.confirmacao_email_service.send_mail",
        side_effect=SMTPException("fora do ar"),
    ):
        for final in range(3):
            resposta = pedir(
                cliente,
                ROTA_REENVIO,
                ip=f"200.130.3.{final}",
                corpo={"emailInstitucional": "202400001@aluno.unb.br"},
            )
            assert resposta.status_code == 200
    assert mail.outbox == []

    pedir(
        cliente,
        ROTA_REENVIO,
        ip=IP_B,
        corpo={"emailInstitucional": "202400001@aluno.unb.br"},
    )

    assert len(mail.outbox) == 1


def test_envios_que_sairam_continuam_contando_depois_de_uma_falha(
    cliente, limite, relogio
):
    limite("reenvio_por_conta", "2/hour")
    criar_conta()
    corpo = {"emailInstitucional": "202400001@aluno.unb.br"}
    pedir(cliente, ROTA_REENVIO, corpo=corpo)
    with mock.patch(
        "apps.cadastro.confirmacao_email_service.send_mail",
        side_effect=SMTPException("fora do ar"),
    ):
        pedir(cliente, ROTA_REENVIO, ip=IP_B, corpo=corpo)
    for final in range(3):
        pedir(cliente, ROTA_REENVIO, ip=f"200.130.4.{final}", corpo=corpo)

    # O 1º saiu, o 2º falhou, só o 3º cabe: 2 no total.
    assert len(mail.outbox) == 2


def test_falha_ao_gravar_o_contador_da_conta_vai_para_o_log(
    cliente, limite, relogio, caplog
):
    limite("reenvio_por_conta")
    conta = criar_conta()
    with (
        mock.patch("apps.cadastro.limite_de_taxa.cache.set", return_value=False),
        caplog.at_level(logging.ERROR, logger="apps.cadastro.limite_de_taxa"),
    ):
        resposta = pedir(
            cliente,
            ROTA_REENVIO,
            corpo={"emailInstitucional": "202400001@aluno.unb.br"},
        )

    assert resposta.status_code == 200
    assert len(mail.outbox) == 1
    # O patch vale para o cache inteiro: o contador por IP também avisa.
    erros = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.ERROR and "da conta" in r.getMessage()
    ]
    assert len(erros) == 1
    assert str(conta.pk) in erros[0]
    assert "202400001" not in erros[0]


def test_falha_na_segunda_gravacao_da_conta_tambem_vai_para_o_log(
    cliente, limite, relogio, caplog
):
    limite("reenvio_por_conta")
    conta = criar_conta()
    corpo = {"emailInstitucional": "202400001@aluno.unb.br"}
    pedir(cliente, ROTA_REENVIO, corpo=corpo)
    relogio.return_value = AGORA + timedelta(seconds=5)

    with (
        mock.patch("apps.cadastro.limite_de_taxa.cache.set", return_value=None),
        caplog.at_level(logging.ERROR, logger="apps.cadastro.limite_de_taxa"),
    ):
        pedir(cliente, ROTA_REENVIO, ip=IP_B, corpo=corpo)

    # O patch vale para o cache inteiro: o contador por IP também avisa.
    erros = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.ERROR and "da conta" in r.getMessage()
    ]
    assert len(erros) == 1
    assert str(conta.pk) in erros[0]


def test_limite_de_uma_conta_nao_atinge_outra(cliente, limite, relogio):
    limite("reenvio_por_conta", "1/hour")
    criar_conta(matricula="202400001")
    criar_conta(matricula="202400002")

    for matricula in ("202400001", "202400001", "202400002"):
        pedir(
            cliente,
            ROTA_REENVIO,
            ip=IP_B,
            corpo={"emailInstitucional": f"{matricula}@aluno.unb.br"},
        )

    assert sorted(m.to[0] for m in mail.outbox) == [
        "202400001@aluno.unb.br",
        "202400002@aluno.unb.br",
    ]


@pytest.mark.parametrize("status", [None, StatusUsuario.ATIVO])
def test_conta_inexistente_ou_confirmada_continua_200_sem_email(
    cliente, limite, relogio, status
):
    limite("reenvio_por_conta", "1/hour")
    if status is not None:
        criar_conta(status=status)

    for _ in range(3):
        resposta = pedir(
            cliente,
            ROTA_REENVIO,
            corpo={"emailInstitucional": "202400001@aluno.unb.br"},
        )
        assert resposta.status_code == 200
    assert mail.outbox == []


def test_primeiro_email_do_cadastro_nao_passa_pelo_limite_da_conta(
    cliente, limite, relogio, django_capture_on_commit_callbacks
):
    """O link do cadastro sai sempre; o limite por conta é só do reenvio."""
    limite("reenvio_por_conta", "1/hour")
    corpo = {
        "tipoUsuario": "estudante",
        "emailInstitucional": "251098732@aluno.unb.br",
        "apelido": "cris",
        "senha": "senha-forte-123",
        "aceitePrivacidade": True,
    }
    with django_capture_on_commit_callbacks(execute=True):
        assert pedir(cliente, ROTA_CADASTRO, corpo=corpo).status_code == 201
    pedir(
        cliente,
        ROTA_REENVIO,
        ip=IP_B,
        corpo={"emailInstitucional": "251098732@aluno.unb.br"},
    )

    # O do cadastro e o primeiro reenvio.
    assert len(mail.outbox) == 2


# --- Cache -------------------------------------------------------------------------


def test_cache_e_compartilhado_entre_os_workers():
    """LocMemCache conta cada worker do Gunicorn separado (guia 4.3)."""
    backend = settings_do_django.CACHES["default"]["BACKEND"]

    assert backend == "django.core.cache.backends.db.DatabaseCache"


def test_cache_cabe_os_contadores_sem_apagar_antes_da_hora():
    opcoes = settings_do_django.CACHES["default"].get("OPTIONS", {})

    # Passou do MAX_ENTRIES, o Django apaga um terço das chaves, inclusive
    # contadores válidos: quem enche a tabela zera os limites dos outros.
    assert opcoes.get("MAX_ENTRIES", 300) >= 100_000


def test_a_tabela_do_cache_existe_depois_do_migrate(db):
    """Criada pela migration 0003 do cadastro: sem ela, login e cadastro dão 500."""
    from django.db import connection

    assert "cache_bandejao" in connection.introspection.table_names()
    cache.set("teste_da_tabela", 1, 30)
    assert cache.get("teste_da_tabela") == 1


# --- Contrato ----------------------------------------------------------------------


@pytest.mark.parametrize("rota", [rota for rota, _ in ROTAS])
def test_contrato_documenta_o_429_limite_excedido(rota):
    from tests.rotas_do_contrato import gerar_schema

    resposta = gerar_schema()["paths"][rota]["post"]["responses"]["429"]

    assert "limite_excedido" in resposta["description"]
    assert "Retry-After" in resposta["description"]
