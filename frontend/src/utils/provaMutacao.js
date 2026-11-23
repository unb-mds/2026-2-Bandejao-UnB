/**
 * PR DE PROVA da FE-17 (fechado sem merge): arquivo crítico novo para mostrar
 * o job `mutacao (front)` reprovando um teste sem asserção real.
 *
 * Nível da fila a partir da espera típica em minutos.
 */
export function nivelDaEspera(minutos) {
  if (minutos == null || minutos < 0) return null
  if (minutos <= 5) return 'vazia'
  if (minutos <= 15) return 'curta'
  if (minutos <= 30) return 'moderada'
  return 'longa'
}
