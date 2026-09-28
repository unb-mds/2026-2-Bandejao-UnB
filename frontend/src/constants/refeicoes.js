/**
 * Tipos de refeição e horários configuráveis (Anexo A do Documento de
 * Requisitos). Usados para escolher a refeição padrão (RF07) e para liberar
 * a avaliação só depois que a refeição começou (RF15).
 */
export const REFEICOES = {
  cafe: {
    id: 'cafe',
    rotulo: 'Café da Manhã',
    rotuloCurto: 'café da manhã',
    inicio: '07:00',
    fim: '09:30',
  },
  almoco: { id: 'almoco', rotulo: 'Almoço', rotuloCurto: 'almoço', inicio: '11:00', fim: '14:30' },
  jantar: { id: 'jantar', rotulo: 'Jantar', rotuloCurto: 'jantar', inicio: '17:00', fim: '19:30' },
}

export const ORDEM_REFEICOES = ['cafe', 'almoco', 'jantar']

/** "11:00" → "11h"; "14:30" → "14h30" */
function formatarHora(hhmm) {
  const [h, m] = hhmm.split(':')
  return m === '00' ? `${Number(h)}h` : `${Number(h)}h${m}`
}

/** Faixa de horário no formato do protótipo: "11h – 14h30". */
export function horarioRefeicao(tipo, separador = ' – ') {
  const refeicao = REFEICOES[tipo]
  return `${formatarHora(refeicao.inicio)}${separador}${formatarHora(refeicao.fim)}`
}

export function horaInicio(tipo) {
  return formatarHora(REFEICOES[tipo].inicio)
}
