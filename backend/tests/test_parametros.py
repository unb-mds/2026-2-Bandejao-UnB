"""Classes de configuração do Anexo A em `config/parametros.py` (BD-04, #90).

A BE-05 cria o arquivo só com o `AvisoPrivacidadeConfig`. A BD-04 acrescenta
as outras classes no mesmo arquivo.
"""

import re
from datetime import date
from pathlib import Path

import pytest

from config.parametros import AvisoPrivacidadeConfig, LimiteDeTaxaConfig

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


# --- LimiteDeTaxaConfig (#123) --------------------------------------------------

LIMITES = ("cadastro_por_ip", "reenvio_por_ip", "reenvio_por_conta", "login_por_ip")


@pytest.mark.parametrize("nome", LIMITES)
def test_limite_de_taxa_tem_o_formato_do_drf(nome):
    """Só a primeira letra da unidade conta: "5/mes" vira 5 por MINUTO, sem
    erro; "5/10m" quebra com KeyError (500 no primeiro pedido).

    Por isso só valem as unidades inteiras, sem número antes delas.
    """
    valor = getattr(LimiteDeTaxaConfig, nome)

    assert re.fullmatch(r"\d+/(second|minute|hour|day)", valor), valor


@pytest.mark.parametrize("nome", LIMITES)
def test_limite_de_taxa_e_positivo(nome):
    numero = int(getattr(LimiteDeTaxaConfig, nome).split("/")[0])

    assert numero > 0


def test_por_que_o_formato_importa():
    """Os dois jeitos de errar o texto, no leitor do próprio DRF (#123)."""
    from apps.cadastro.limite_de_taxa import ler_limite

    assert ler_limite("5/mes") == (5, 60)
    with pytest.raises(KeyError):
        ler_limite("5/10m")
