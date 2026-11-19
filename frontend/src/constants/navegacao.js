export const ITENS_NAVEGACAO = [
  { rotulo: 'Início', rota: 'inicio', icone: 'casa', preenche: true },
  { rotulo: 'Cardápio', rota: 'cardapio', icone: 'talheres' },
  { rotulo: 'Fila', rota: 'fila', icone: 'relogio' },
  { rotulo: 'Avaliações', rota: 'avaliacoes', icone: 'estrela', preenche: true },
  { rotulo: 'Perfil', rota: 'inicio', icone: 'usuario' },
]

export function itemAtivo(item, nomeDaRota) {
  return item.rota !== 'inicio' && Boolean(nomeDaRota?.toString().startsWith(item.rota))
}
