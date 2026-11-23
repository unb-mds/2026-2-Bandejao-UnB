import { REFEICOES } from '@/constants/refeicoes'

const NIVEIS = ['vazia', 'curta', 'moderada', 'longa']

const MOVIMENTO = {
  cafe: [0, 1, 2, 3, 2, 1, 1, 0, 0, 0],
  almoco: [0, 1, 1, 2, 3, 3, 2, 3, 2, 1, 1, 0, 0, 0],
  jantar: [0, 1, 2, 3, 3, 2, 1, 1, 0, 0],
}

const CAMPI_SEM_DADOS = new Set([5])

const paraMinutos = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}

const paraHora = (minutos) =>
  `${String(Math.floor(minutos / 60)).padStart(2, '0')}:${String(minutos % 60).padStart(2, '0')}:00`

export function previsaoSimulada(campus, tipoRefeicao, data) {
  const base = { campus, tipoRefeicao, data }
  if (CAMPI_SEM_DADOS.has(campus)) return { ...base, status: 'dados_insuficientes', faixas: [] }
  const movimento = MOVIMENTO[tipoRefeicao]
  const maior = Math.max(...movimento)
  const inicio = paraMinutos(REFEICOES[tipoRefeicao].inicio)
  const faixas = movimento.map((valor, i) => ({
    inicio: paraHora(inicio + i * 15),
    fim: paraHora(inicio + (i + 1) * 15),
    nivel: NIVEIS[valor],
    ehPico: valor === maior,
  }))
  return { ...base, status: 'disponivel', faixas }
}
