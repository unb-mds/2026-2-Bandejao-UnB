export const ITENS_NAVEGACAO = [
  { rotulo: 'Início', rota: 'inicio', icone: 'casa', preenche: true },
  { rotulo: 'Cardápio', rota: 'cardapio', icone: 'talheres', ativaEm: 'campus-tela' },
  { rotulo: 'Fila', rotuloLateral: 'Fila do RU', rota: 'fila', icone: 'relogio' },
  { rotulo: 'Avaliações', rota: 'avaliacoes', icone: 'estrela', preenche: true },
  { rotulo: 'Perfil', rota: 'progresso', icone: 'usuario' },
]

// No tablet, Perfil também leva ao progresso.
export const ITENS_NAVEGACAO_TOPO = ITENS_NAVEGACAO

// No desktop, o acesso à conta já fica no atalho da barra lateral.
export const ITENS_NAVEGACAO_LATERAL = ITENS_NAVEGACAO.filter((item) => item.rota !== 'progresso')

/**
 * A barra inferior não marca Início, pois não aparece nessa tela.
 * A do topo e a lateral passam `marcarInicio` para marcar a Início.
 * Uma rota acende o item de mesmo nome ou com o nome dele mais "-"
 * (`cardapio-campus` acende Cardápio; `filas-historico` não acende Fila).
 */
export function itemAtivo(item, nomeDaRota, { marcarInicio = false } = {}) {
  if (!nomeDaRota) return false
  const nome = String(nomeDaRota)
  if (item.rota === 'inicio') return marcarInicio && nome === 'inicio'
  return nome === item.rota || nome === item.ativaEm || nome.startsWith(`${item.rota}-`)
}
