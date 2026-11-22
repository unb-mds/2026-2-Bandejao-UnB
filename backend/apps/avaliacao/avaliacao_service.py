"""AvaliacaoService: avaliar uma refeição, com a pontuação (RF15.1, Avaliação N4 4a)."""

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction

from apps.avaliacao.avaliacao_repository import (
    AvaliacaoJaExisteError,
    AvaliacaoRepository,
)
from apps.avaliacao.comentario_validator import ComentarioValidator
from apps.avaliacao.erros import AvaliacaoIndisponivelError
from apps.avaliacao.janela_avaliacao_validator import JanelaAvaliacaoValidator
from apps.avaliacao.models import Avaliacao
from apps.avaliacao.nota_validator import NotaValidator
from apps.cardapio.models import Refeicao
from apps.gamificacao.pontuacao_service import (
    PontuacaoService,
    RefeicaoRef,
    ResultadoPontuacao,
    TipoContribuicao,
)


@dataclass(frozen=True)
class AvaliacaoRegistrada:
    avaliacao: Avaliacao
    pontos: ResultadoPontuacao

    @property
    def criada(self) -> bool:
        """Primeira avaliação da refeição (201); a editada tem `editada_em`."""
        return self.avaliacao.editada_em is None


class AvaliacaoService:
    def __init__(self):
        self.janela = JanelaAvaliacaoValidator()
        self.nota = NotaValidator()
        self.comentario = ComentarioValidator()
        self.repositorio = AvaliacaoRepository()
        self.pontuacao = PontuacaoService()

    def avaliar(
        self,
        conta,
        refeicao: Refeicao,
        nota,
        comentario: str | None,
        agora: datetime,
    ) -> AvaliacaoRegistrada:
        """Sempre um upsert: a segunda avaliação da refeição edita a primeira.

        Confere janela, nota e comentário, nessa ordem: com a refeição
        fechada, o motivo de indisponível vale mais que um erro no formulário.
        Avaliação e pontos ficam na mesma transação: se a pontuação falhar,
        nada fica gravado e a pessoa tenta de novo (ADR 0011).
        """
        if not self.janela.pode_avaliar(refeicao, agora):
            raise AvaliacaoIndisponivelError
        self.nota.validar(nota)
        comentario = self.comentario.validar(comentario)
        with transaction.atomic():
            avaliacao = self._gravar(conta, refeicao, nota, comentario, agora)
            # Sempre chama, também na edição: quem decide se pontua (check-in
            # na mesma refeição, uma vez só) é a Gamificação. A refeição é a
            # avaliada, nunca um campo do PWA (RN09).
            pontos = self.pontuacao.registrar_contribuicao(
                conta,
                TipoContribuicao.AVALIACAO,
                avaliacao.id,
                RefeicaoRef(
                    campus=refeicao.campus,
                    tipo_refeicao=refeicao.tipo,
                    data=refeicao.data,
                ),
            )
        return AvaliacaoRegistrada(avaliacao=avaliacao, pontos=pontos)

    def _gravar(self, conta, refeicao, nota, comentario, agora) -> Avaliacao:
        existente = self.repositorio.buscar_por_conta_e_refeicao(
            conta, refeicao, travar=True
        )
        editada = True
        if existente is None:
            try:
                return self.repositorio.inserir(
                    Avaliacao(
                        usuario=conta,
                        refeicao=refeicao,
                        nota=nota,
                        comentario=comentario,
                    )
                )
            except AvaliacaoJaExisteError:
                # Duplo toque: a outra requisição inseriu primeiro. A pessoa
                # avaliou uma vez só, então a avaliação não vira "editada".
                existente = self.repositorio.buscar_por_conta_e_refeicao(
                    conta, refeicao, travar=True
                )
                editada = False
        existente.nota = nota
        existente.comentario = comentario
        if editada:
            existente.editada_em = agora
        return self.repositorio.salvar_edicao(existente)
