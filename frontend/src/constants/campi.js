/**
 * Campi da UnB com restaurante universitário (glossário: "Campus").
 * O Restaurante Executivo do Darcy Ribeiro está fora do escopo (RI08).
 */
export const CAMPI = [
  { id: 'darcy', nome: 'Darcy Ribeiro', descricao: 'Asa Norte, Brasília' },
  { id: 'ceilandia', nome: 'Ceilândia', descricao: 'Campus FCE' },
  { id: 'gama', nome: 'Gama (FGA)', descricao: 'Campus Gama' },
  { id: 'planaltina', nome: 'Planaltina', descricao: 'Campus FUP' },
  { id: 'fal', nome: 'Fazenda Água Limpa', descricao: 'Campus FAL' },
]

export function buscarCampus(id) {
  return CAMPI.find((campus) => campus.id === id) ?? null
}

export function campusValido(id) {
  return CAMPI.some((campus) => campus.id === id)
}

/** Monograma exibido na lista de campi (ex.: "Darcy Ribeiro" → "DR"). */
export function siglaCampus(nome) {
  return nome
    .split(' ')
    .map((palavra) => palavra[0])
    .join('')
    .slice(0, 3)
}
