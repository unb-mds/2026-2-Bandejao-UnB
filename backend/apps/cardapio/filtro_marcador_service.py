"""FiltroMarcadorService: sinaliza os pratos com marcador escolhido (RF08, N4 4a).

Analogia: é o marca-texto, não a tesoura. Nenhum prato sai da resposta; o
serviço só pinta os que têm algum marcador selecionado e avisa quando uma
categoria ficou toda pintada ("sem opção compatível").
"""

from apps.cardapio.cardapio_filtrado import CategoriaFiltrada, PratoFiltrado
from apps.cardapio.models import Categoria, Prato


def _pratos_na_ordem(categoria: Categoria) -> list[Prato]:
    return sorted(categoria.pratos.all(), key=lambda p: (p.ordem, p.id))


def _marcadores_do_prato(prato: Prato) -> list[str]:
    # Ordem de id (a da fixture), para a resposta ser sempre a mesma.
    return [m.nome for m in sorted(prato.marcadores.all(), key=lambda m: m.id)]


class FiltroMarcadorService:
    def aplicar(
        self,
        categorias: list[Categoria],
        marcadores_selecionados: list[str],
        alergenos_indisponivel: bool,
    ) -> list[CategoriaFiltrada]:
        """Uma `CategoriaFiltrada` por categoria, na ordem recebida.

        Com `alergenos_indisponivel`, o filtro fica desativado (RF08, RF06.3):
        nenhum prato é sinalizado e nenhuma categoria fica sem opção. Quem
        põe `filtro_marcador_desativado` na resposta é o CardapioQueryService.
        """
        selecionados = set() if alergenos_indisponivel else set(marcadores_selecionados)
        resultado = []
        for categoria in categorias:
            pratos = _pratos_na_ordem(categoria)
            filtrados = []
            for prato in pratos:
                marcadores = _marcadores_do_prato(prato)
                filtrados.append(
                    PratoFiltrado(
                        descricao=prato.nome,
                        marcadores=marcadores,
                        contem_marcador_selecionado=bool(
                            selecionados.intersection(marcadores)
                        ),
                    )
                )
            resultado.append(
                CategoriaFiltrada(
                    nome=categoria.nome,
                    sem_opcao_compativel=self._contem_todos_marcados(
                        pratos, selecionados
                    ),
                    pratos=filtrados,
                )
            )
        return resultado

    def _contem_todos_marcados(
        self, pratos: list[Prato], marcadores_selecionados: set[str]
    ) -> bool:
        """True se **todos** os pratos têm algum marcador selecionado.

        Categoria vazia não fica "sem opção compatível": não há prato com
        marcador nenhum para sinalizar.
        """
        if not pratos or not marcadores_selecionados:
            return False
        return all(
            marcadores_selecionados.intersection(_marcadores_do_prato(prato))
            for prato in pratos
        )
