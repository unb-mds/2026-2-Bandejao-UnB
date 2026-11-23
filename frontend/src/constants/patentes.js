/**
 * Patentes do Anexo A (RN11), na ordem dos limiares. `id` é o valor que a
 * API devolve (`GET /api/gamificacao/progresso/` e `GET /api/ranking/`).
 */
export const PATENTES = [
  { id: 'CALOURO_DE_BANDEJA', rotulo: 'Calouro de Bandeja' },
  { id: 'RATO_DE_RU', rotulo: 'Rato de RU' },
  { id: 'VETERANO', rotulo: 'Veterano' },
  { id: 'MESTRE_DA_FILA', rotulo: 'Mestre da Fila' },
  { id: 'LENDA_DO_RU', rotulo: 'Lenda do RU' },
]

/** Nome da patente para a tela. Um valor desconhecido aparece como veio. */
export function rotuloPatente(valor) {
  return PATENTES.find((patente) => patente.id === valor)?.rotulo ?? valor ?? ''
}
