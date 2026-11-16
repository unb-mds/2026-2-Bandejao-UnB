"""O validador de matrícula deve consumir a configuração do Anexo A."""

from datetime import date

from apps.cadastro.validadores import MatriculaValidator
from config.parametros import ParametrosCadastroConfig


def test_validador_respeita_primeiro_ano_configurado(monkeypatch):
    monkeypatch.setattr(ParametrosCadastroConfig, "primeiro_ano_matricula", 20)
    validador = MatriculaValidator(hoje=date(2026, 11, 16))

    assert validador.validar_prefixo_ano_semestre("191234567") is False
    assert validador.validar_prefixo_ano_semestre("201234567") is True
