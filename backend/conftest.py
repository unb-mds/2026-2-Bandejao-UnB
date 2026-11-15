"""Configuração compartilhada do pytest.

A SECRET_KEY de teste vem do pytest.ini (pytest-env), porque o pytest-django
importa o settings antes de este arquivo ser carregado. Assim quem clona o
repositório e roda `pytest` direto (ou o CI da BE-02) não precisa de um .env.
"""

import importlib.util
from pathlib import Path

import pytest

CAMINHO_SETTINGS = Path(__file__).resolve().parent / "config" / "settings.py"

# Variáveis que o settings.py lê com o decouple.
VARIAVEIS_DO_SETTINGS = [
    "DEBUG",
    "ALLOWED_HOSTS",
    "DB_ENGINE",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_AGE",
    "CSRF_COOKIE_SECURE",
    "CSRF_TRUSTED_ORIGINS",
    "ATRAS_DE_PROXY_HTTPS",
    "EMAIL_BACKEND",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_USE_TLS",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "DEFAULT_FROM_EMAIL",
    "URL_DO_PWA",
]


# Variáveis sem valor padrão em produção (sem DEBUG): o settings não carrega
# sem elas. Os testes que não tratam delas recebem estes valores.
OBRIGATORIAS_DE_TESTE = {
    "SECRET_KEY": "chave-so-para-teste",
    "URL_DO_PWA": "https://pwa.teste",
    "EMAIL_HOST": "smtp.teste",
    "EMAIL_HOST_USER": "usuario-teste",
    "EMAIL_HOST_PASSWORD": "senha-teste",
}


@pytest.fixture
def carregar_settings(monkeypatch):
    """Devolve uma função que executa o config/settings.py do zero.

    Serve para testar o valor PADRÃO das configurações: o .env do desenvolvedor
    é ignorado e só as variáveis passadas como argumento existem, além das
    obrigatórias em produção (`OBRIGATORIAS_DE_TESTE`). Passe `None` para tirar
    uma delas, como em `carregar(URL_DO_PWA=None)`.
    O módulo carregado é uma cópia isolada, então o `django.conf.settings`
    usado pelo resto da suíte não é afetado.
    """
    import decouple

    def carregar(**ambiente):
        # Config sem repositório = ignora o arquivo .env (só lê os.environ).
        monkeypatch.setattr(
            decouple, "config", decouple.Config(decouple.RepositoryEmpty())
        )
        for nome in VARIAVEIS_DO_SETTINGS:
            monkeypatch.delenv(nome, raising=False)
        for nome, valor in {**OBRIGATORIAS_DE_TESTE, **ambiente}.items():
            if valor is None:
                monkeypatch.delenv(nome, raising=False)
            else:
                monkeypatch.setenv(nome, valor)

        spec = importlib.util.spec_from_file_location(
            "settings_isolado", CAMINHO_SETTINGS
        )
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo

    return carregar


@pytest.fixture
def usuario(db):
    """Usuário comum, já com o aviso de privacidade aceito."""
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    return get_user_model().objects.create_user(
        matricula_siape="202400001",
        tipo_usuario="estudante",
        apelido="cris",
        email_institucional="202400001@aluno.unb.br",
        aceite_privacidade_em=timezone.now(),
        versao_aviso_aceita="teste",
        password="senha-forte-123",
    )
