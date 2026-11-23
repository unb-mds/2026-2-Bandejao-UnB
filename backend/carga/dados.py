"""Dados do teste de carga (BD-14, #184).

Popula um banco **vazio** com o volume que torna as respostas realistas:

- a semana de hoje publicada nos 5 campi, com café, almoço e jantar todos os
  dias, 4 categorias e 3 pratos com marcadores em cada refeição;
- check-ins nas 4 semanas da janela da previsão (Fila N4 4c), hoje fora,
  espalhados pelas faixas de 15 min de cada refeição, sem conta (como depois
  da retenção da BD-11: nenhum dado pessoal no teste).

Uso, com os campi e marcadores da fixture já carregados (`loaddata campi
marcadores`):

    python manage.py shell -c "from carga.dados import main; main()"

Recusa um banco que já tem check-ins, para nunca rodar em produção.
"""

import os
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.cardapio.models import (
    Campus,
    Categoria,
    Dieta,
    FonteCardapio,
    Marcador,
    Prato,
    Refeicao,
    StatusLeitura,
    TipoRefeicao,
)
from apps.fila.faixa_horario_generator import FaixaHorarioGenerator
from apps.fila.models import Checkin
from config.parametros import HorariosRefeicaoConfig, ParametrosFilaConfig

HORARIOS = {
    TipoRefeicao.CAFE: HorariosRefeicaoConfig.horario_cafe,
    TipoRefeicao.ALMOCO: HorariosRefeicaoConfig.horario_almoco,
    TipoRefeicao.JANTAR: HorariosRefeicaoConfig.horario_jantar,
}
CATEGORIAS = ("Salada", "Prato principal", "Guarnição", "Sobremesa")
PRATOS_POR_CATEGORIA = 3
LOTE = 2000


class BancoNaoVazioError(RuntimeError):
    """O banco já tem check-ins: não é um banco de teste."""


class SemCampiError(RuntimeError):
    """Faltam os campi da fixture (`loaddata campi marcadores`)."""


@dataclass(frozen=True)
class Resumo:
    campi: int
    refeicoes: int
    pratos: int
    checkins: int


def popular(hoje: date, checkins_por_refeicao: int = 200, semente: int = 14) -> Resumo:
    """Cria a semana de `hoje` e os check-ins das 4 semanas anteriores.

    `checkins_por_refeicao` é o número de check-ins de cada campus, em cada
    refeição de cada dia da janela.
    """
    if Checkin.objects.exists():
        raise BancoNaoVazioError(
            "O banco já tem check-ins. O teste de carga só popula um banco "
            "vazio, nunca o de produção."
        )
    campi = list(Campus.objects.order_by("pk"))
    if not campi:
        raise SemCampiError("Rode antes: python manage.py loaddata campi marcadores")

    # Sorteio com semente: os dados do teste são os mesmos a cada rodada.
    sorteio = random.Random(semente)
    with transaction.atomic():
        refeicoes, pratos = _cardapio_da_semana(campi, hoje, sorteio)
        checkins = _checkins_da_janela(campi, hoje, checkins_por_refeicao, sorteio)
    return Resumo(
        campi=len(campi), refeicoes=refeicoes, pratos=pratos, checkins=checkins
    )


def _cardapio_da_semana(campi, hoje: date, sorteio) -> tuple[int, int]:
    segunda = hoje - timedelta(days=hoje.weekday())
    marcadores = list(Marcador.objects.order_by("pk"))
    agora = timezone.now()
    total_refeicoes = total_pratos = 0
    for campus in campi:
        FonteCardapio.objects.create(
            campus=campus,
            semana_inicio=segunda,
            url=f"https://ru.unb.br/carga-{campus.pk}-{segunda.isoformat()}.pdf",
            sha256="0" * 64,
            verificado_em=agora,
            processado_em=agora,
        )
        for dia in range(7):
            data = segunda + timedelta(days=dia)
            for tipo, (inicio, fim) in HORARIOS.items():
                refeicao = Refeicao.objects.create(
                    campus=campus,
                    data=data,
                    tipo=tipo,
                    horario_inicio=inicio,
                    horario_fim=fim,
                    status_leitura=StatusLeitura.OK,
                    fonte_pdf_url="https://ru.unb.br/carga.pdf",
                )
                total_refeicoes += 1
                total_pratos += _categorias(refeicao, marcadores, sorteio)
    return total_refeicoes, total_pratos


def _categorias(refeicao, marcadores, sorteio) -> int:
    criados = 0
    for ordem, nome in enumerate(CATEGORIAS, start=1):
        categoria = Categoria.objects.create(refeicao=refeicao, nome=nome, ordem=ordem)
        for posicao in range(1, PRATOS_POR_CATEGORIA + 1):
            prato = Prato.objects.create(
                categoria=categoria,
                nome=f"{nome} {posicao}",
                dieta=sorteio.choice(list(Dieta)),
                ordem=posicao,
            )
            if marcadores:
                prato.marcadores.add(*sorteio.sample(marcadores, 2))
            criados += 1
    return criados


def _checkins_da_janela(campi, hoje: date, por_refeicao: int, sorteio) -> int:
    gerador = FaixaHorarioGenerator()
    faixas = {tipo: gerador.faixas(tipo) for tipo in HORARIOS}
    dias = 7 * ParametrosFilaConfig.janela_semanas
    lote: list[Checkin] = []
    total = 0
    for atras in range(dias, 0, -1):
        data = hoje - timedelta(days=atras)
        for campus in campi:
            for tipo, faixas_do_tipo in faixas.items():
                for _ in range(por_refeicao):
                    lote.append(
                        Checkin(
                            usuario=None,
                            campus=campus,
                            tipo_refeicao=tipo,
                            data=data,
                            registrado_em=None,
                            faixa_inicio=sorteio.choice(faixas_do_tipo).inicio,
                            tempo_espera_min=_tempo_de_espera(sorteio),
                        )
                    )
                    if len(lote) >= LOTE:
                        total += len(Checkin.objects.bulk_create(lote))
                        lote = []
    if lote:
        total += len(Checkin.objects.bulk_create(lote))
    return total


def _tempo_de_espera(sorteio) -> Decimal | None:
    """Metade dos check-ins com o tempo da pergunta de saída (RF22)."""
    if sorteio.random() < 0.5:
        return None
    return Decimal(sorteio.choice(("2.5", "7.5", "12.0", "15.5")))


def main() -> None:
    """Para o `manage.py shell -c`: o volume vem de CARGA_CHECKINS."""
    por_refeicao = int(os.environ.get("CARGA_CHECKINS", "200"))
    resumo = popular(timezone.localdate(), checkins_por_refeicao=por_refeicao)
    print(
        f"Campi: {resumo.campi}; refeições: {resumo.refeicoes}; "
        f"pratos: {resumo.pratos}; check-ins: {resumo.checkins}"
    )
