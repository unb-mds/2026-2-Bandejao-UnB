"""FonteCardapioConfig: de onde vem o PDF de cada campus (Leitor N4 4c).

Segue o padrão da `LocalizacaoCampusConfig`: o que é de cada campus (rótulo
do título na página do RU e prefixo do nome do arquivo) vem das colunas de
`CAMPUS`, povoadas por fixture (BD-16). A URL da página só repassa a
`ParametrosLeitorConfig` (Anexo A, BD-04), que lê o settings a cada acesso.
Se o RU renomear um título, o ajuste é na fixture, sem mudar o código.
"""

from apps.cardapio.models import Campus
from config.parametros import ParametrosLeitorConfig


class FonteCardapioConfig:
    @property
    def url_pagina(self) -> str:
        return ParametrosLeitorConfig().url_pagina

    @staticmethod
    def rotulo(campus: Campus) -> str:
        """Nome do campus no título do bloco ("Cardápio <rótulo>")."""
        return campus.rotulo_pagina_ru

    @staticmethod
    def prefixo_arquivo(campus: Campus) -> str:
        """Início esperado do nome do PDF do campus ("Darcy-Ribeiro")."""
        return campus.prefixo_arquivo_pdf
