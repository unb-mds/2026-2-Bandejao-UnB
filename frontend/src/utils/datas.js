/**
 * Funções de data/hora. Todas trabalham no fuso local do aparelho e usam
 * datas no formato ISO curto ("2026-09-28"), que é o formato trocado com a API.
 */

const DIAS_CURTOS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const DIAS_LONGOS = [
  'Domingo',
  'Segunda-feira',
  'Terça-feira',
  'Quarta-feira',
  'Quinta-feira',
  'Sexta-feira',
  'Sábado',
]
const MESES = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]

const dois = (n) => String(n).padStart(2, '0')

export function paraISO(data) {
  return `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}`
}

export function deISO(iso) {
  const [ano, mes, dia] = iso.split('-').map(Number)
  return new Date(ano, mes - 1, dia)
}

export function hojeISO(agora = new Date()) {
  return paraISO(agora)
}

export function somarDias(iso, dias) {
  const data = deISO(iso)
  data.setDate(data.getDate() + dias)
  return paraISO(data)
}

/** Segunda-feira da semana de `agora`, em ISO. */
export function inicioDaSemana(agora = new Date()) {
  const data = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate())
  const deslocamento = (data.getDay() + 6) % 7
  data.setDate(data.getDate() - deslocamento)
  return paraISO(data)
}

/** "11:30" → 690 */
export function minutosDoDia(hhmm) {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}

export function minutosAgora(agora = new Date()) {
  return agora.getHours() * 60 + agora.getMinutes()
}

/** "2026-09-28" → "Seg" */
export function diaCurto(iso) {
  return DIAS_CURTOS[deISO(iso).getDay()]
}

/** "2026-09-28" → "Segunda" */
export function diaLongoSemFeira(iso) {
  return DIAS_LONGOS[deISO(iso).getDay()].replace('-feira', '')
}

/** "2026-09-28" → "28/09" */
export function diaMes(iso) {
  const data = deISO(iso)
  return `${dois(data.getDate())}/${dois(data.getMonth() + 1)}`
}

/** Date → "Segunda-feira, 28 de setembro de 2026" */
export function dataPorExtenso(agora = new Date()) {
  return `${DIAS_LONGOS[agora.getDay()]}, ${agora.getDate()} de ${MESES[agora.getMonth()]} de ${agora.getFullYear()}`
}

/** Instante ISO completo → "agora", "há 5 min", "há 2h", "ontem", "há 3 dias". */
export function tempoRelativo(instanteISO, agora = new Date()) {
  const minutos = Math.floor((agora - new Date(instanteISO)) / 60000)
  if (minutos < 1) return 'agora'
  if (minutos < 60) return `há ${minutos} min`
  const horas = Math.floor(minutos / 60)
  if (horas < 24) return `há ${horas}h`
  const dias = Math.floor(horas / 24)
  return dias === 1 ? 'ontem' : `há ${dias} dias`
}
