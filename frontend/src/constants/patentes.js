/**
 * Limiares iniciais do Anexo A (RN11). A patente mostrada vem sempre do
 * servidor: pela RN11 ela não regride, então o front não a recalcula a
 * partir dos pontos.
 */
export const PATENTES = [
  { id: 'CALOURO_DE_BANDEJA', rotulo: 'Calouro de Bandeja', minimo: 0 },
  { id: 'RATO_DE_RU', rotulo: 'Rato de RU', minimo: 150 },
  { id: 'VETERANO', rotulo: 'Veterano', minimo: 450 },
  { id: 'MESTRE_DA_FILA', rotulo: 'Mestre da Fila', minimo: 900 },
  { id: 'LENDA_DO_RU', rotulo: 'Lenda do RU', minimo: 1500 },
]

export const IDS_PATENTES = PATENTES.map((patente) => patente.id)

export function rotuloPatente(id) {
  return PATENTES.find((patente) => patente.id === id)?.rotulo ?? null
}

export function proximaPatente(id) {
  const indice = IDS_PATENTES.indexOf(id)
  return indice >= 0 ? (PATENTES[indice + 1] ?? null) : null
}
