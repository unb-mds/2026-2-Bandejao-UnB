"""Settings de produção lidos do ambiente (BD-05, #91).

Os nomes das variáveis são os combinados na divisão da BD-05: o Compose
repassa o `.env` da VM ao backend sem alterar nada. As quatro do Django têm o
prefixo `DJANGO_`; as do banco e do e-mail mantêm os nomes de antes.
"""

import importlib.util
import re
from pathlib import Path

import pytest
from decouple import UndefinedValueError
from django.core.exceptions import ImproperlyConfigured

# O .env de produção combinado na BD-05, com valores de exemplo.
ENV_DE_PRODUCAO = {
    "DJANGO_SECRET_KEY": "chave-de-producao-de-teste",
    "DJANGO_DEBUG": "False",
    "DJANGO_ALLOWED_HOSTS": "bandejaounb.com.br,www.bandejaounb.com.br",
    "DJANGO_CSRF_TRUSTED_ORIGINS": (
        "https://bandejaounb.com.br,https://www.bandejaounb.com.br"
    ),
    "URL_DO_PWA": "https://bandejaounb.com.br",
    "DB_ENGINE": "mysql",
    "DB_HOST": "db",
    "DB_PORT": "3306",
    "DB_NAME": "bandejao",
    "DB_USER": "app_bandejao",
    "DB_PASSWORD": "senha-do-banco",
    "EMAIL_HOST": "smtp-relay.brevo.com",
    "EMAIL_PORT": "587",
    "EMAIL_HOST_USER": "login-smtp@brevo",
    "EMAIL_HOST_PASSWORD": "chave-smtp",
    "EMAIL_USE_TLS": "True",
    "DEFAULT_FROM_EMAIL": "nao-responda@bandejaounb.com.br",
}


@pytest.fixture
def producao(carregar_settings):
    return carregar_settings(**ENV_DE_PRODUCAO)


def test_django_le_as_variaveis_com_prefixo(producao):
    assert producao.SECRET_KEY == "chave-de-producao-de-teste"
    assert producao.DEBUG is False
    assert producao.ALLOWED_HOSTS == ["bandejaounb.com.br", "www.bandejaounb.com.br"]
    assert producao.CSRF_TRUSTED_ORIGINS == [
        "https://bandejaounb.com.br",
        "https://www.bandejaounb.com.br",
    ]


def test_django_debug_liga_o_modo_de_desenvolvimento(carregar_settings):
    assert carregar_settings(DJANGO_DEBUG="True").DEBUG is True


def test_sem_django_debug_o_padrao_e_producao(carregar_settings):
    assert carregar_settings(DJANGO_DEBUG=None).DEBUG is False


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("1", True), ("on", True), ("0", False), ("off", False), ("", False)],
)
def test_django_debug_aceita_as_formas_de_booleano(carregar_settings, valor, esperado):
    ambiente = {**ENV_DE_PRODUCAO, "DJANGO_DEBUG": valor}

    assert carregar_settings(**ambiente).DEBUG is esperado


def test_django_debug_invalido_para_a_subida(carregar_settings):
    """Um erro de digitação não pode virar False (ou True) em silêncio."""
    with pytest.raises(ValueError):
        carregar_settings(**{**ENV_DE_PRODUCAO, "DJANGO_DEBUG": "Fasle"})


def test_producao_sem_secret_key_nao_sobe(carregar_settings):
    with pytest.raises(UndefinedValueError, match="DJANGO_SECRET_KEY"):
        carregar_settings(**{**ENV_DE_PRODUCAO, "DJANGO_SECRET_KEY": None})


def test_producao_sem_allowed_hosts_nao_sobe(carregar_settings):
    """Sem a lista, o Django responde 400 a tudo: melhor parar na subida."""
    with pytest.raises(UndefinedValueError, match="DJANGO_ALLOWED_HOSTS"):
        carregar_settings(**{**ENV_DE_PRODUCAO, "DJANGO_ALLOWED_HOSTS": None})


@pytest.mark.parametrize("vazio", ["", " , "])
def test_producao_com_allowed_hosts_vazio_nao_sobe(carregar_settings, vazio):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        carregar_settings(**{**ENV_DE_PRODUCAO, "DJANGO_ALLOWED_HOSTS": vazio})


def test_desenvolvimento_dispensa_allowed_hosts(carregar_settings):
    """Com DEBUG e a lista vazia, o Django já aceita localhost e 127.0.0.1."""
    dev = carregar_settings(DJANGO_DEBUG="True", DJANGO_ALLOWED_HOSTS=None)

    assert dev.ALLOWED_HOSTS == []


@pytest.mark.parametrize(
    ("antigo", "novo"),
    [
        ("SECRET_KEY", "DJANGO_SECRET_KEY"),
        ("DEBUG", "DJANGO_DEBUG"),
        ("ALLOWED_HOSTS", "DJANGO_ALLOWED_HOSTS"),
        ("CSRF_TRUSTED_ORIGINS", "DJANGO_CSRF_TRUSTED_ORIGINS"),
    ],
)
def test_nome_antigo_no_env_para_a_subida(carregar_settings, antigo, novo):
    """Um .env de antes da BD-05 não pode ser ignorado em silêncio.

    Sem o aviso, um `DEBUG=True` esquecido viraria produção, e um
    `ALLOWED_HOSTS` antigo deixaria a lista vazia.
    """
    with pytest.raises(ImproperlyConfigured, match=novo):
        carregar_settings(**{**ENV_DE_PRODUCAO, antigo: "qualquer"})


def test_varios_nomes_antigos_aparecem_juntos_na_mensagem(carregar_settings):
    """A pessoa corrige o .env de uma vez, sem subir o servidor várias vezes."""
    with pytest.raises(ImproperlyConfigured) as erro:
        carregar_settings(
            **{**ENV_DE_PRODUCAO, "SECRET_KEY": "x", "DEBUG": "True"},
        )

    assert "SECRET_KEY -> DJANGO_SECRET_KEY" in str(erro.value)
    assert "DEBUG -> DJANGO_DEBUG" in str(erro.value)


def test_nome_antigo_vindo_do_arquivo_env(carregar_settings, monkeypatch, tmp_path):
    """O caso da VM: o nome antigo está no arquivo .env, e não no ambiente."""
    import decouple

    arquivo = tmp_path / ".env"
    arquivo.write_text("DEBUG=True\n", encoding="utf-8")
    monkeypatch.setattr(
        decouple, "RepositoryEmpty", lambda: decouple.RepositoryEnv(str(arquivo))
    )

    with pytest.raises(ImproperlyConfigured, match="DEBUG -> DJANGO_DEBUG"):
        carregar_settings(**ENV_DE_PRODUCAO)


def test_banco_le_as_variaveis_do_env(producao):
    banco = producao.DATABASES["default"]

    assert banco["ENGINE"] == "django.db.backends.mysql"
    assert banco["HOST"] == "db"
    assert banco["PORT"] == "3306"
    assert banco["NAME"] == "bandejao"
    assert banco["USER"] == "app_bandejao"
    assert banco["PASSWORD"] == "senha-do-banco"
    assert banco["OPTIONS"]["charset"] == "utf8mb4"
    assert banco["OPTIONS"]["isolation_level"] == "read committed"


def test_email_le_as_variaveis_do_env(producao):
    opcoes = producao.MAILERS["default"]["OPTIONS"]

    assert producao.MAILERS["default"]["BACKEND"] == (
        "django.core.mail.backends.smtp.EmailBackend"
    )
    assert opcoes["host"] == "smtp-relay.brevo.com"
    assert opcoes["port"] == 587
    assert opcoes["use_tls"] is True
    assert opcoes["username"] == "login-smtp@brevo"
    assert opcoes["password"] == "chave-smtp"
    assert producao.DEFAULT_FROM_EMAIL == "nao-responda@bandejaounb.com.br"


def test_producao_liga_os_cookies_seguros_e_o_proxy(producao):
    """Itens do `check --deploy` que dependem só do settings (o comando em si
    roda no CI e na VM, com o settings de verdade)."""
    assert producao.DEBUG is False
    assert producao.SESSION_COOKIE_SECURE is True
    assert producao.CSRF_COOKIE_SECURE is True
    assert producao.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_toda_variavel_do_settings_e_isolada_nos_testes():
    """O `carregar_settings` apaga do ambiente as variáveis que conhece. Uma
    variável nova fora da lista vazaria do .env ou do pytest.ini para os
    testes de valor padrão."""
    caminho = Path(__file__).resolve().parents[1] / "conftest.py"
    spec = importlib.util.spec_from_file_location("conftest_isolado", caminho)
    conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conftest)

    codigo = conftest.CAMINHO_SETTINGS.read_text(encoding="utf-8")
    lidas = set(
        re.findall(r'config(?:_sem_padrao_em_producao)?\(\s*"([A-Z_]+)"', codigo)
    )
    conhecidas = set(conftest.VARIAVEIS_DO_SETTINGS) | set(
        conftest.OBRIGATORIAS_DE_TESTE
    )

    assert lidas, "nenhuma variável encontrada no settings.py"
    assert lidas <= conhecidas, f"faltam no conftest.py: {lidas - conhecidas}"
