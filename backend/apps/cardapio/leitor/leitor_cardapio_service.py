"""LeitorCardapioService: o orquestrador único do Leitor (C4 4a, 4b e 4c).

Analogia: é o chefe de cozinha que confere a entrega. Para cada campus, ele
pede ao carteiro (`CardapioDownloader`) os PDFs da página do RU, um por
semana; se a caixa é a mesma da última entrega (mesma URL e mesmo SHA-256),
nem abre. Se mudou, manda ler (`CardapioPDFParser`), confere as datas e
guarda tudo de uma vez (`CardapioRepository`, numa transação). Qualquer
problema vira alerta (`AlertaEquipeService`), e o cardápio válido anterior
fica onde está (RF06.4).

O relógio (`agora`) vem de fora, lido uma vez pelo comando `ler_cardapio`.
"""

import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.cardapio.leitor.alerta_equipe_service import AlertaEquipeService
from apps.cardapio.leitor.cardapio_downloader import CardapioDownloader, FontePDF
from apps.cardapio.leitor.cardapio_pdf_parser import (
    AssociacaoFalhouError,
    CardapioPDFParser,
    DownloadError,
    FonteNaoEncontradaError,
    FormatoPDFInvalidoError,
    LegendaInvalidaError,
    RefeicaoEstruturada,
)
from apps.cardapio.leitor.cardapio_repository import CardapioRepository
from apps.cardapio.models import Campus, FonteCardapio, Refeicao, TipoAlerta
from config.parametros import ParametrosLeitorConfig

# Classe da falha guardada pelo parser na página só em texto -> tipo do alerta.
TIPO_DO_ALERTA_SO_EM_TEXTO = {
    LegendaInvalidaError: TipoAlerta.LEGENDA_INVALIDA,
    AssociacaoFalhouError: TipoAlerta.ASSOCIACAO_FALHOU,
}


def _data(dia: date | None) -> str:
    return f"{dia:%d/%m/%Y}" if dia else "?"


def _semana(fonte: FontePDF) -> str:
    if fonte.inicio is None:
        return f"link {fonte.texto_link!r}"
    return f"semana de {_data(fonte.inicio)} a {_data(fonte.fim)}"


@dataclass
class ResultadoLeitura:
    """O que a execução fez num campus, para o resumo do comando."""

    lidas: int = 0
    sem_mudanca: int = 0
    alertas: int = 0


class LeitorCardapioService:
    def __init__(self):
        self.downloader = CardapioDownloader()
        self.repositorio = CardapioRepository()
        self.alertas = AlertaEquipeService()
        self.parametros = ParametrosLeitorConfig()

    def processar(self, campus: Campus, agora: datetime) -> ResultadoLeitura:
        """Lê o cardápio de um campus: todas as semanas da página do RU.

        1. Descoberta dos links (falha do campus inteiro: alerta e para).
        2. Cada semana à parte: download, SHA-256, leitura, datas, gravação.
        3. Cardápio não publicado depois de segunda, 12h (ADR 0014).
        4. Sem nenhum alerta nesta execução, o contador do campus zera.
        """
        resultado = ResultadoLeitura()
        try:
            fontes = self.downloader.localizar_pdfs(campus)
        except (FonteNaoEncontradaError, DownloadError) as exc:
            # Página fora do ar, título ausente ou repetido: nenhum link é
            # confiável, e o "não publicado" não é avaliado.
            self._alertar(
                TipoAlerta.FALHA_LEITURA_PDF,
                campus,
                f"Etapa: descoberta do PDF na página do RU. {exc}. Último "
                "cardápio válido mantido.",
                agora,
                resultado,
            )
            return resultado

        for fonte in fontes:
            self._processar_semana(campus, fonte, agora, resultado)

        if self._semana_atrasada(fontes, agora):
            segunda = self._segunda_vigente(agora)
            self._alertar(
                TipoAlerta.FALHA_LEITURA_PDF,
                campus,
                "Etapa: cardápio não publicado. Nenhum link da semana de "
                f"{_data(segunda)} a {_data(segunda + timedelta(days=6))} "
                f"no bloco do campus na página do RU "
                f"({self.downloader.config.url_pagina}) depois do prazo "
                "(segunda-feira, 12h).",
                agora,
                resultado,
            )

        if resultado.alertas == 0:
            self.alertas.zerar_contador(campus, agora=agora)
        return resultado

    # ------------------------------------------------------------- semana

    def _processar_semana(
        self,
        campus: Campus,
        fonte: FontePDF,
        agora: datetime,
        resultado: ResultadoLeitura,
    ) -> None:
        if fonte.erro is not None:
            self._alertar(
                TipoAlerta.FALHA_LEITURA_PDF,
                campus,
                f"Etapa: descoberta do PDF ({_semana(fonte)}). {fonte.erro}. "
                "Último cardápio válido mantido.",
                agora,
                resultado,
            )
            return

        # O link foi achado: `verificado_em` anda em toda execução, mesmo
        # que o download ou a leitura falhem depois (C4 4c, FonteCardapio).
        anterior = FonteCardapio.objects.filter(
            campus=campus, semana_inicio=fonte.inicio
        )
        anterior.update(verificado_em=agora)
        anterior = anterior.first()

        try:
            arquivo = self.downloader.baixar(fonte)
        except (DownloadError, FormatoPDFInvalidoError) as exc:
            etapa = "download" if isinstance(exc, DownloadError) else "formato"
            self._falha_da_semana(campus, fonte, etapa, exc, agora, resultado)
            return

        if (
            anterior is not None
            and anterior.url == fonte.url
            and anterior.sha256 == arquivo.sha256
        ):
            resultado.sem_mudanca += 1
            return

        try:
            refeicoes, _avisos = CardapioPDFParser(
                io.BytesIO(arquivo.conteudo)
            ).extrair()
        except FormatoPDFInvalidoError as exc:
            self._falha_da_semana(campus, fonte, "formato", exc, agora, resultado)
            return
        try:
            self._conferir_datas(fonte, [d for r in refeicoes for d in r.dias])
        except FormatoPDFInvalidoError as exc:
            self._falha_da_semana(campus, fonte, "datas", exc, agora, resultado)
            return

        with transaction.atomic():
            gravadas = []
            for refeicao in refeicoes:
                gravadas += self.repositorio.salvar(campus, fonte, refeicao)
                if refeicao.alergenos_indisponiveis:
                    for dia in refeicao.dias:
                        self.repositorio.marcar_alergenos_indisponivel(
                            campus, refeicao.refeicao, date.fromisoformat(dia["data"])
                        )
            self.repositorio.remover_ausentes(campus, fonte, gravadas)
            FonteCardapio.objects.update_or_create(
                campus=campus,
                semana_inicio=fonte.inicio,
                defaults={
                    "url": fonte.url,
                    "sha256": arquivo.sha256,
                    "verificado_em": agora,
                    "processado_em": agora,
                },
            )
        resultado.lidas += 1

        # Depois da transação: o alerta aponta para a refeição já gravada.
        for refeicao in refeicoes:
            if refeicao.alergenos_indisponiveis:
                self._alertar_so_em_texto(campus, fonte, refeicao, agora, resultado)

    def _falha_da_semana(self, campus, fonte, etapa, exc, agora, resultado):
        havia = self.repositorio.manter_ultimo_valido(campus, fonte)
        situacao = (
            "Último cardápio válido mantido."
            if havia
            else "Semana sem cardápio anterior: segue como não publicada."
        )
        # As mensagens do download já trazem a URL; as do parser, não.
        url = "" if fonte.url in str(exc) else f" URL: {fonte.url}."
        self._alertar(
            TipoAlerta.FALHA_LEITURA_PDF,
            campus,
            f"Etapa: {etapa} ({_semana(fonte)}). {exc}.{url} {situacao}",
            agora,
            resultado,
        )

    def _alertar_so_em_texto(
        self,
        campus: Campus,
        fonte: FontePDF,
        refeicao: RefeicaoEstruturada,
        agora: datetime,
        resultado: ResultadoLeitura,
    ) -> None:
        """Uma linha de alerta por página (refeição da semana), presa à
        refeição do primeiro dia; os dias vão na mensagem."""
        tipo = TIPO_DO_ALERTA_SO_EM_TEXTO[refeicao.falha]
        dias = [date.fromisoformat(d["data"]) for d in refeicao.dias]
        primeira = Refeicao.objects.get(
            campus=campus, data=dias[0], tipo=refeicao.refeicao
        )
        self._alertar(
            tipo,
            campus,
            f"Etapa: marcadores ({_semana(fonte)}). A página do {refeicao.refeicao} "
            f"foi publicada só em texto, sem marcadores, nos dias "
            f"{', '.join(_data(d) for d in dias)}. Motivo: {refeicao.motivo}. "
            f"URL: {fonte.url}.",
            agora,
            resultado,
            refeicao=primeira,
        )

    def _alertar(self, tipo, campus, detalhe, agora, resultado, refeicao=None):
        self.alertas.registrar_alerta(
            tipo, campus, detalhe, refeicao=refeicao, agora=agora
        )
        resultado.alertas += 1

    # ------------------------------------------------- conferências (C4)

    @staticmethod
    def _conferir_datas(fonte: FontePDF, dias: list[dict[str, str]]) -> None:
        """Todos os dias lidos do PDF dentro do intervalo do link.

        Não exige igualdade: o PDF só traz os dias em que o campus serve
        refeição (o Gama tem 5 ou 6 num link de 7, RF06.2).
        """
        for dia in dias:
            data = date.fromisoformat(dia["data"])
            if not fonte.inicio <= data <= fonte.fim:
                raise FormatoPDFInvalidoError(
                    f"o dia {_data(data)} do PDF está fora do intervalo do link "
                    f"({_data(fonte.inicio)} a {_data(fonte.fim)})"
                )

    def _segunda_vigente(self, agora: datetime) -> date:
        hoje = timezone.localtime(agora).date()
        return hoje - timedelta(days=hoje.weekday())

    def _semana_atrasada(self, fontes: list[FontePDF], agora: datetime) -> bool:
        """Nenhum link do bloco é da semana vigente, e já passou o prazo.

        Contam todos os links com datas legíveis, inclusive os reprovados na
        conferência do arquivo ou repetidos (ADR 0014). O prazo é o do Anexo
        A: segunda-feira, 12h, no horário de Brasília.
        """
        local = timezone.localtime(agora)
        hoje = local.date()
        if any(f.inicio is not None and f.inicio <= hoje <= f.fim for f in fontes):
            return False
        segunda = self._segunda_vigente(agora)
        prazo = datetime.combine(
            segunda + timedelta(days=self.parametros.dia_alerta_nao_publicado),
            self.parametros.horario_alerta_nao_publicado,
            tzinfo=local.tzinfo,
        )
        return local >= prazo
