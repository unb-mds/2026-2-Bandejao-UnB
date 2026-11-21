"""FiltroDietaService: esconde as linhas de prato fora da dieta (RF09, N4 4a).

Analogia: é o garçom que tira da mesa as travessas que você disse que não
come. Ele olha o que está dentro (a dieta dos pratos) mas leva a travessa
inteira (a categoria), porque todos os pratos de uma categoria têm a mesma
dieta (o Leitor copia a dieta da linha do PDF para cada prato dela).
"""

from apps.cardapio.dieta_selecionada import DietaSelecionada
from apps.cardapio.models import Categoria, Dieta, Refeicao

# Dietas de prato que cada escolha deixa passar. `None` é a dieta nula das
# categorias comuns a todas as dietas (saladas, guarnição, sopa): nunca saem.
DIETAS_PERMITIDAS = {
    DietaSelecionada.OVOLACTOVEGETARIANO: {
        Dieta.OVOLACTO,
        Dieta.VEGETARIANO_ESTRITO,
        None,
    },
    DietaSelecionada.VEGETARIANO_ESTRITO: {Dieta.VEGETARIANO_ESTRITO, None},
}


class FiltroDietaService:
    def aplicar(self, refeicao: Refeicao, dieta: DietaSelecionada) -> list[Categoria]:
        """Categorias da refeição que sobram na dieta, na ordem do PDF.

        `SEM_FILTRO` devolve todas, inclusive a categoria vazia. Nas outras
        dietas, a categoria fica só se **todos** os pratos dela têm uma dieta
        permitida; a categoria vazia não tem prato de dieta proibida e fica.
        """
        categorias = sorted(refeicao.categorias.all(), key=lambda c: (c.ordem, c.id))
        if dieta == DietaSelecionada.SEM_FILTRO:
            return categorias
        permitidas = DIETAS_PERMITIDAS[dieta]
        return [
            categoria
            for categoria in categorias
            if all(prato.dieta in permitidas for prato in categoria.pratos.all())
        ]
