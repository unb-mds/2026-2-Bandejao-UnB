/**
 * Campi da UnB com restaurante universitário (glossário: "Campus").
 * O Restaurante Executivo do Darcy Ribeiro está fora do escopo (RI08).
 *
 * `idApi` é o id do campus no backend (`GET /api/campi/`), o que vai no
 * corpo do `POST /api/checkins/`. São os `pk` da fixture
 * `backend/apps/cardapio/fixtures/campi.json`.
 * TODO(FE-E3): ler a lista de `GET /api/campi/` em vez de fixar os ids aqui.
 */
export const CAMPI = [
  { id: 'darcy', idApi: 1, nome: 'Darcy Ribeiro', descricao: 'Asa Norte, Brasília' },
  { id: 'ceilandia', idApi: 2, nome: 'Ceilândia', descricao: 'Campus FCE' },
  { id: 'gama', idApi: 3, nome: 'Gama (FGA)', descricao: 'Campus Gama' },
  { id: 'planaltina', idApi: 4, nome: 'Planaltina', descricao: 'Campus FUP' },
  { id: 'fal', idApi: 5, nome: 'Fazenda Água Limpa', descricao: 'Campus FAL' },
]

export function buscarCampus(id) {
  return CAMPI.find((campus) => campus.id === id) ?? null
}

export function buscarCampusPorIdApi(idApi) {
  return CAMPI.find((campus) => campus.idApi === idApi) ?? null
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
