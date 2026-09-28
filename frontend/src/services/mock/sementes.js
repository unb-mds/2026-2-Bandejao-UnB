/**
 * Avaliações "pré-existentes" do backend simulado, geradas de forma
 * determinística para cada refeição que já começou. Assim as telas têm
 * médias e comentários realistas sem precisar de milhares de registros.
 */
import { REFEICOES } from '@/constants/refeicoes'
import { deISO, hojeISO, minutosAgora, minutosDoDia } from '@/utils/datas'
import { inicioSemanaVigente } from './cardapios'

const COMENTARIOS_PROTOTIPO = [
  {
    apelido: 'maria_s',
    nota: 5,
    comentario: 'Frango grelhado excelente hoje, porção bem servida e tudo quentinho.',
  },
  {
    apelido: 'joao_fga',
    nota: 4,
    comentario: 'Comida boa como sempre. Fila tranquila no horário do almoço.',
  },
  {
    apelido: 'cristina_m',
    nota: 3,
    comentario: 'Regular. O purê estava sem sal, mas o frango compensou.',
  },
  {
    apelido: 'lucas_unb',
    nota: 5,
    comentario: 'Opção vegetariana ótima! Tofu muito bem temperado.',
  },
]

const COMENTARIOS_GERAIS = [
  { apelido: 'ana_bio', nota: 4, comentario: 'Salada fresquinha e o feijão estava no ponto.' },
  { apelido: 'pedro_eng', nota: 2, comentario: 'Arroz um pouco empapado hoje. O resto estava ok.' },
  { apelido: 'bia_l', nota: 5, comentario: 'Sobremesa maravilhosa, voltaria só por ela!' },
  {
    apelido: 'rafa_fce',
    nota: 4,
    comentario: 'Bem servido e saiu rápido. Recomendo a opção vegana.',
  },
  { apelido: 'gui_fup', nota: 3, comentario: 'Comida ok, mas poderia ter mais tempero.' },
  { apelido: 'carol_unb', nota: 5, comentario: 'Melhor refeição da semana até agora.' },
  { apelido: 'thiago_m', nota: 4, comentario: 'Bom custo-benefício como sempre.' },
  { apelido: 'lari_s', nota: 3, comentario: 'O prato principal estava frio quando cheguei.' },
]

/** Apelidos já usados pelas avaliações semente (reservados no cadastro). */
export const APELIDOS_SEMENTE = [...COMENTARIOS_PROTOTIPO, ...COMENTARIOS_GERAIS].map(
  (c) => c.apelido,
)

/** Números do protótipo para a segunda-feira do Darcy Ribeiro. */
const FIXOS_DARCY_SEGUNDA = {
  cafe: { quantidade: 92, media: 3.9 },
  almoco: { quantidade: 187, media: 4.3, comentarios: COMENTARIOS_PROTOTIPO },
  jantar: { quantidade: 134, media: 4.1 },
}

function hashTexto(texto) {
  let hash = 7
  for (const caractere of texto) hash = (Math.imul(hash, 31) + caractere.codePointAt(0)) >>> 0
  return hash
}

function instante(dataISO, minutos) {
  const data = deISO(dataISO)
  data.setMinutes(minutos)
  return data
}

/**
 * Devolve { soma, quantidade, comentarios } das avaliações semente de uma
 * refeição, considerando apenas o que já "aconteceu" até `agora`.
 */
export function avaliacoesSemente(campus, data, tipo, agora = new Date()) {
  const vazio = { soma: 0, quantidade: 0, comentarios: [] }
  const hoje = hojeISO(agora)
  const inicio = minutosDoDia(REFEICOES[tipo].inicio)
  const fim = minutosDoDia(REFEICOES[tipo].fim)
  if (data > hoje || (data === hoje && minutosAgora(agora) < inicio)) return vazio

  const hash = hashTexto(`${campus}|${data}|${tipo}`)
  const fixo =
    campus === 'darcy' && data === inicioSemanaVigente(agora) ? FIXOS_DARCY_SEGUNDA[tipo] : null
  let quantidade = fixo?.quantidade ?? 40 + (hash % 150)
  const media = fixo?.media ?? 3.3 + ((hash >> 3) % 15) / 10
  let comentarios =
    fixo?.comentarios ??
    Array.from(
      { length: 2 + (hash % 3) },
      (_, i) => COMENTARIOS_GERAIS[(hash + i * 3) % COMENTARIOS_GERAIS.length],
    )

  // Refeição de hoje ainda em andamento: só parte das avaliações já chegou,
  // e os comentários se distribuem entre o início da refeição e agora.
  let ultimoMinuto = fim
  if (data === hoje) {
    const decorridos = minutosAgora(agora) - inicio
    quantidade = Math.floor(quantidade * Math.min(1, (decorridos + 1) / (fim - inicio)))
    ultimoMinuto = Math.min(fim, minutosAgora(agora))
  }

  const passo = (ultimoMinuto - inicio) / (comentarios.length + 1)
  comentarios = comentarios
    .slice(0, quantidade)
    .map((c, i) => ({
      ...c,
      criadaEm: instante(data, inicio + Math.round(passo * (comentarios.length - i))),
    }))
    .filter((c) => c.criadaEm <= agora)
    .map((c, i) => ({ id: `semente-${hash}-${i}`, ...c, criadaEm: c.criadaEm.toISOString() }))

  return { soma: Math.round(media * quantidade), quantidade, comentarios }
}
