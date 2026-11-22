"""Parâmetros de consulta comuns às rotas públicas com `campus` e data.

Saíram da `CardapioView` (BE-11, #217) para o resumo das avaliações (BE-13)
seguir o mesmo critério: 400 `parametros_invalidos` para formato errado e
404 `campus_nao_encontrado` para o id bem formado que não está no banco.
"""

import re
from datetime import date

from rest_framework.exceptions import NotFound, ParseError

from apps.cardapio.models import Campus

# Só dígitos ASCII: `int()` aceitaria " 1", "+1" e dígitos de outras escritas.
SO_DIGITOS = re.compile(r"[0-9]+")
# Dígitos do maior pk possível (BigAutoField, 2**63 - 1). Um id com mais
# dígitos não existe em banco nenhum e nem chega ao `int()`.
DIGITOS_DO_MAIOR_ID = len(str(2**63 - 1))
# AAAA-MM-DD: `date.fromisoformat` aceitaria também "20261123".
FORMATO_DATA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# Faixa aceita nas datas (`semana` e `dia` do cardápio, `data` do resumo das
# avaliações). Longe dos extremos do `date` (anos 1 e
# 9999), onde somar ou subtrair a semana daria OverflowError (500).
DATA_MINIMA = date(2000, 1, 1)
DATA_MAXIMA = date(2099, 12, 31)


class ParametrosInvalidos(ParseError):
    """400 `parametros_invalidos` no formato `{codigo, mensagem}`.

    O `tratador_de_excecoes` (config/excecoes.py) usa o `code` e a mensagem
    da exceção. Não é o `ValidationError` do DRF de propósito: o detalhe dele
    é uma lista, e o tratador o deixaria no formato padrão de validação. O
    `code` é obrigatório: sem ele, o `ParseError` sairia como `json_invalido`.
    """

    def __init__(self, mensagem):
        super().__init__(mensagem, code="parametros_invalidos")


def ler_id_do_campus(valor):
    """Confere só o formato e devolve o id como `int`, ou None se não cabe.

    Ausente ou fora de "só dígitos" dá 400. Só dígitos, mas com mais dígitos
    que o maior pk, devolve None: o campus não existe, e `buscar_campus` dá o
    404. Sem esse corte, o `int()` levantaria `ValueError` acima de 4300
    dígitos (500). Entre o 2**63 e os 19 dígitos, o estouro fica com o
    IntegerFieldOverflow do Django, conferido em teste.
    """
    if valor is None:
        raise ParametrosInvalidos("Informe o campus.")
    if not SO_DIGITOS.fullmatch(valor):
        raise ParametrosInvalidos("O campus deve ser o id numérico de GET /api/campi/.")
    digitos = valor.lstrip("0") or "0"
    if len(digitos) > DIGITOS_DO_MAIOR_ID:
        return None
    return int(digitos)


def buscar_campus(campus_id):
    """404 `campus_nao_encontrado` para id bem formado que não está no banco.

    É o caso do link antigo ou do campus removido (#217). O `codigo` é o
    mesmo do contrato do ranking, e a store do cardápio decide por ele
    (FE-08, #144). O `code=` é o que o `tratador_de_excecoes` usa; sem ele,
    sairia `nao_encontrado`. `campus_id` None é o id que não cabe no pk.
    """
    campus = None
    if campus_id is not None:
        campus = Campus.objects.filter(pk=campus_id).first()
    if campus is None:
        raise NotFound("Não existe campus com esse id.", code="campus_nao_encontrado")
    return campus


def ler_data(valor, nome):
    if valor is None:
        return None
    try:
        if not FORMATO_DATA.fullmatch(valor):
            raise ValueError
        data = date.fromisoformat(valor)
    except ValueError:
        raise ParametrosInvalidos(
            f"O parâmetro {nome} deve ser uma data válida no formato AAAA-MM-DD."
        ) from None
    if not DATA_MINIMA <= data <= DATA_MAXIMA:
        raise ParametrosInvalidos(
            f"O parâmetro {nome} deve ser uma data entre "
            f"{DATA_MINIMA.isoformat()} e {DATA_MAXIMA.isoformat()}."
        )
    return data
