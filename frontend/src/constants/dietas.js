/**
 * Dietas do filtro (RF09). Cada categoria do cardápio pertence a uma linha:
 * "todas" (comum a todas as dietas), "padrao", "ovolacto" ou "vegano".
 */
export const DIETAS = [
  { id: 'todos', rotulo: 'Todos' },
  { id: 'ovolacto', rotulo: 'Ovolactovegetariano' },
  { id: 'vegano', rotulo: 'Vegetariano Estrito' },
]

export function rotuloDieta(id) {
  return DIETAS.find((d) => d.id === id)?.rotulo ?? id
}

/** Linhas de dieta que continuam visíveis para cada filtro. */
export const LINHAS_VISIVEIS = {
  todos: ['todas', 'padrao', 'ovolacto', 'vegano'],
  ovolacto: ['todas', 'ovolacto', 'vegano'],
  vegano: ['todas', 'vegano'],
}
