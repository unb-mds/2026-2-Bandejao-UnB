export const DIETAS = [
  { id: 'sem_filtro', rotulo: 'Sem filtro' },
  { id: 'ovolactovegetariano', rotulo: 'Ovolactovegetariano' },
  { id: 'vegetariano_estrito', rotulo: 'Vegetariano estrito' },
]

export const DIETA_PADRAO = 'sem_filtro'

export const DIETAS_ANTIGAS = {
  todos: 'sem_filtro',
  ovolacto: 'ovolactovegetariano',
  vegano: 'vegetariano_estrito',
}

export function rotuloDieta(id) {
  return DIETAS.find((d) => d.id === id)?.rotulo ?? id
}
