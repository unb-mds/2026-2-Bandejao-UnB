"""Apoio dos testes da Exposição do Cardápio (BE-11, #138).

Cria campus, marcadores, refeições, categorias, pratos e a linha da
`FonteCardapio` direto no banco de teste, sem passar pelo Leitor (BE-12).

Datas usadas nos testes (fuso America/Sao_Paulo):
- semana de 23/11/2026 (segunda) a 29/11/2026 (domingo);
- semana seguinte começa em 30/11/2026 (segunda).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.cardapio.models import (
    Campus,
    Categoria,
    FonteCardapio,
    Marcador,
    Prato,
    Refeicao,
    StatusLeitura,
    TipoRefeicao,
)
from config.parametros import HorariosRefeicaoConfig

BRASILIA = ZoneInfo("America/Sao_Paulo")

SEGUNDA = date(2026, 11, 23)
TERCA = date(2026, 11, 24)
SABADO = date(2026, 11, 28)
DOMINGO = date(2026, 11, 29)
PROXIMA_SEGUNDA = date(2026, 11, 30)

# Os 10 nomes da fixture `marcadores.json` (BD-03).
NOMES_MARCADORES = (
    "cogumelo",
    "leite_e_derivados",
    "mel",
    "pimenta",
    "soja",
    "trigo_gluten",
    "amendoim",
    "oleaginosa",
    "ovo",
    "suino",
)

HORARIOS = {
    TipoRefeicao.CAFE: HorariosRefeicaoConfig.horario_cafe,
    TipoRefeicao.ALMOCO: HorariosRefeicaoConfig.horario_almoco,
    TipoRefeicao.JANTAR: HorariosRefeicaoConfig.horario_jantar,
}


def em_brasilia(dia: date, hora: time) -> datetime:
    """`dia` e `hora` no horário de Brasília, como datetime com fuso."""
    return datetime.combine(dia, hora, tzinfo=BRASILIA)


def criar_campus(nome="Gama") -> Campus:
    coordenada = Decimal("-15.989493")
    return Campus.objects.create(
        nome=nome,
        ru_latitude=coordenada,
        ru_longitude=coordenada,
        raio_confirmacao_metros=150,
        centro_latitude=coordenada,
        centro_longitude=coordenada,
        raio_deteccao_metros=150,
        rotulo_pagina_ru=nome,
        prefixo_arquivo_pdf=nome,
    )


def criar_marcadores() -> None:
    """Os 10 marcadores, com os mesmos nomes da fixture."""
    for nome in NOMES_MARCADORES:
        Marcador.objects.get_or_create(nome=nome)


def criar_refeicao(
    campus, data, tipo=TipoRefeicao.ALMOCO, status_leitura=StatusLeitura.OK
) -> Refeicao:
    inicio, fim = HORARIOS[tipo]
    return Refeicao.objects.create(
        campus=campus,
        data=data,
        tipo=tipo,
        horario_inicio=inicio,
        horario_fim=fim,
        status_leitura=status_leitura,
        fonte_pdf_url="https://ru.unb.br/cardapio.pdf",
    )


def criar_categoria(refeicao, nome, ordem, pratos=()) -> Categoria:
    """Categoria com os pratos dados como `(nome, dieta, [marcadores])`.

    A ordem dos pratos é a da lista, igual à do PDF.
    """
    categoria = Categoria.objects.create(refeicao=refeicao, nome=nome, ordem=ordem)
    for posicao, (nome_prato, dieta, marcadores) in enumerate(pratos, start=1):
        prato = Prato.objects.create(
            categoria=categoria, nome=nome_prato, dieta=dieta, ordem=posicao
        )
        prato.marcadores.add(*Marcador.objects.filter(nome__in=marcadores))
    return categoria


def publicar_semana(campus, inicio: date) -> FonteCardapio:
    """Linha da `FonteCardapio`: o PDF da semana de `inicio` foi lido."""
    agora = timezone.now()
    return FonteCardapio.objects.create(
        campus=campus,
        semana_inicio=inicio,
        url=f"https://ru.unb.br/cardapio-{inicio.isoformat()}.pdf",
        sha256="0" * 64,
        verificado_em=agora,
        processado_em=agora,
    )


def dias_da_semana(inicio: date, quantidade=7) -> list[date]:
    return [inicio + timedelta(days=n) for n in range(quantidade)]
