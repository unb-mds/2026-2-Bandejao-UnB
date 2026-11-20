export const ITENS_NAVEGACAO = [
  { rotulo: 'Início', rota: 'inicio', icone: 'casa', preenche: true },
  { rotulo: 'Cardápio', rota: 'cardapio', icone: 'talheres' },
  { rotulo: 'Fila', rota: 'fila', icone: 'relogio' },
  { rotulo: 'Avaliações', rota: 'avaliacoes', icone: 'estrela', preenche: true },
  // "Perfil" é um atalho para a Início, onde ficam o apelido, o campus e o login.
  { rotulo: 'Perfil', rota: 'inicio', icone: 'usuario', atalhoDaInicio: true },
]

// A barra do topo aparece também na Início: lá o "Perfil" seria um segundo
// link para o mesmo lugar, com outro nome (WCAG 2.4.4).
export const ITENS_NAVEGACAO_TOPO = ITENS_NAVEGACAO.filter((item) => !item.atalhoDaInicio)

/**
 * Como no protótipo, a barra inferior nunca marca "Início" nem "Perfil" (ela
 * nem aparece na Início). A do topo passa `marcarInicio` para marcar a Início.
 * Uma rota acende o item de mesmo nome ou com o nome dele mais "-"
 * (`cardapio-campus` acende Cardápio; `filas-historico` não acende Fila).
 */
export function itemAtivo(item, nomeDaRota, { marcarInicio = false } = {}) {
  if (!nomeDaRota || item.atalhoDaInicio) return false
  const nome = String(nomeDaRota)
  if (item.rota === 'inicio') return marcarInicio && nome === 'inicio'
  return nome === item.rota || nome.startsWith(`${item.rota}-`)
}
