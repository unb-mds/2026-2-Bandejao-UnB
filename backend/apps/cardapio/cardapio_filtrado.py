"""Objetos de resposta do cardápio filtrado (Exposição N4 4a).

`CardapioFiltrado`, `CategoriaFiltrada`, `PratoFiltrado` e `StatusCardapio`
são o que o `CardapioQueryService` monta. A `CardapioView` converte para o
`CardapioFiltradoSerializer`, que tem os nomes do contrato (camelCase).
"""

from dataclasses import dataclass
from datetime import date

from django.db import models

from apps.cardapio.models import Campus

# Aviso curto do RF07.1, igual ao da `CardapioView.vue`: a tela não muda
# quando o front passar a usar o campo. O aviso longo do filtro (RF08, que
# cita peixe e frutos do mar, L04) fica no `FiltroCardapio.vue`, no front.
AVISO_SUJEITO_A_ALTERACAO = (
    "Cardápio sujeito a alteração. A ausência de marcador não garante que o "
    "prato esteja livre do ingrediente."
)


class StatusCardapio(models.TextChoices):
    PUBLICADO = "publicado", "Publicado"
    NAO_PUBLICADO = "nao_publicado", "Não publicado"


@dataclass(frozen=True)
class PratoFiltrado:
    # Vem de `Prato.nome`; no contrato o campo se chama `descricao`.
    descricao: str
    marcadores: list[str]
    contem_marcador_selecionado: bool


@dataclass(frozen=True)
class CategoriaFiltrada:
    nome: str
    sem_opcao_compativel: bool
    pratos: list[PratoFiltrado]


@dataclass(frozen=True)
class CardapioFiltrado:
    campus: Campus
    refeicao: str
    # Dia exibido: pode diferir do pedido (RN05, item 5).
    data: date
    refeicao_encerrada: bool
    status: StatusCardapio
    alergenos_indisponivel: bool
    filtro_marcador_desativado: bool
    categorias: list[CategoriaFiltrada]
    aviso_sujeito_a_alteracao: str = AVISO_SUJEITO_A_ALTERACAO
