"""Classes de configuração do Anexo A em `config/parametros.py` (BD-04, #90).

A BE-05 cria o arquivo só com o `AvisoPrivacidadeConfig`. A BD-04 acrescenta
as outras classes no mesmo arquivo.
"""

from datetime import date

from config.parametros import AvisoPrivacidadeConfig



def test_versao_atual_do_aviso_e_a_data_do_aviso_em_aaaa_mm_dd():
    """Formato combinado na #90: a data do aviso de privacidade em vigor."""
    versao = AvisoPrivacidadeConfig.versao_atual

    assert date.fromisoformat(versao).isoformat() == versao


def test_versao_atual_cabe_na_coluna_versao_aviso_aceita():
    from apps.cadastro.models import Usuario

    campo = Usuario._meta.get_field("versao_aviso_aceita")
    assert len(AvisoPrivacidadeConfig.versao_atual) <= campo.max_length

