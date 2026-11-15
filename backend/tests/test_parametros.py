"""Classes de configuração do Anexo A em `config/parametros.py` (BD-04, #90).

A BE-05 cria o arquivo só com o `AvisoPrivacidadeConfig`. A BD-04 acrescenta
as outras classes no mesmo arquivo.
"""

import re
from datetime import date
from pathlib import Path

from config.parametros import AvisoPrivacidadeConfig

TEXTO_DO_AVISO = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "requisitos"
    / "aviso-de-privacidade.md"
)


def test_versao_atual_do_aviso_e_a_data_do_aviso_em_aaaa_mm_dd():
    """Formato combinado na #90: a data do aviso de privacidade em vigor."""
    versao = AvisoPrivacidadeConfig.versao_atual

    assert date.fromisoformat(versao).isoformat() == versao


def test_versao_atual_cabe_na_coluna_versao_aviso_aceita():
    from apps.cadastro.models import Usuario

    campo = Usuario._meta.get_field("versao_aviso_aceita")
    assert len(AvisoPrivacidadeConfig.versao_atual) <= campo.max_length


def test_versao_atual_e_a_do_texto_do_aviso():
    """Trocou o texto do aviso? Troque a data nos dois lugares (DOC-03)."""
    versao_do_texto = re.search(
        r"^\*\*Versão:\*\* (\S+)$",
        TEXTO_DO_AVISO.read_text(encoding="utf-8"),
        re.MULTILINE,
    )

    assert versao_do_texto, f"{TEXTO_DO_AVISO} sem a linha **Versão:**"
    assert versao_do_texto.group(1) == AvisoPrivacidadeConfig.versao_atual
