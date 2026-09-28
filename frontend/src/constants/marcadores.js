/**
 * Os 10 marcadores da legenda do cardápio oficial (glossário: "Marcador").
 */
export const MARCADORES = [
  { id: 'cogumelo', rotulo: 'Cogumelo' },
  { id: 'leite', rotulo: 'Leite e derivados' },
  { id: 'mel', rotulo: 'Mel' },
  { id: 'pimenta', rotulo: 'Pimenta' },
  { id: 'soja', rotulo: 'Soja' },
  { id: 'trigo', rotulo: 'Trigo/Glúten' },
  { id: 'amendoim', rotulo: 'Amendoim' },
  { id: 'oleaginosa', rotulo: 'Oleaginosa' },
  { id: 'ovo', rotulo: 'Ovo' },
  { id: 'suino', rotulo: 'Suíno' },
]

export const IDS_MARCADORES = MARCADORES.map((m) => m.id)

export function rotuloMarcador(id) {
  return MARCADORES.find((m) => m.id === id)?.rotulo ?? id
}
