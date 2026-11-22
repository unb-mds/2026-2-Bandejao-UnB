import { REFEICOES, ORDEM_REFEICOES } from '@/constants/refeicoes'
import { DIETA_PADRAO } from '@/constants/dietas'
import { hojeISO, inicioDaSemana, minutosAgora, minutosDoDia, somarDias } from './datas'

/**
 * Refeição exibida por padrão (RF07): a que está em andamento; se nenhuma
 * estiver, a próxima do dia; depois da última, a última do dia.
 */
export function refeicaoPadrao(tiposDisponiveis, agora = new Date()) {
  const tipos = ORDEM_REFEICOES.filter((tipo) => tiposDisponiveis.includes(tipo))
  if (tipos.length === 0) return null
  const minutos = minutosAgora(agora)
  const emAndamentoOuProxima = tipos.find((tipo) => minutos <= minutosDoDia(REFEICOES[tipo].fim))
  return emAndamentoOuProxima ?? tipos[tipos.length - 1]
}

/**
 * Dia e refeição iniciais para uma semana de cardápio: hoje, se hoje tiver
 * cardápio; senão o próximo dia com cardápio; senão o primeiro da semana.
 */
export function selecaoPadrao(dias, agora = new Date()) {
  if (!dias?.length) return { data: null, refeicao: null }
  const hoje = hojeISO(agora)
  const dia = dias.find((d) => d.data === hoje) ?? dias.find((d) => d.data > hoje) ?? dias[0]
  const tipos = dia.refeicoes.map((r) => r.tipo)
  const refeicao = dia.data === hoje ? refeicaoPadrao(tipos, agora) : tipos[0]
  return { data: dia.data, refeicao }
}

/**
 * Dias das abas do cardápio (RF07.1): a semana inteira, de segunda a domingo,
 * como o backend define — o domingo pertence à semana da segunda anterior.
 * O Darcy Ribeiro serve aos domingos; nos outros campi a aba mostra
 * "sem serviço".
 */
export function diasDaSemanaVigente(agora = new Date()) {
  const segunda = inicioDaSemana(agora)
  return Array.from({ length: 7 }, (_, i) => somarDias(segunda, i))
}

export function contarFiltrosAtivos(dieta, marcadores) {
  return (dieta !== DIETA_PADRAO ? 1 : 0) + marcadores.length
}

/**
 * Resumo de até três linhas para o cartão "Cardápio de hoje" da Home:
 * prato principal padrão, acompanhamentos e salada (ou, na falta delas —
 * como no café da manhã —, as primeiras categorias da refeição).
 */
export function resumoRefeicao(categorias) {
  const buscar = (trecho) =>
    categorias.find((c) => c.rotulo.toLowerCase().startsWith(trecho) && c.pratos.length)
  const preferidas = [
    ['Prato principal', buscar('prato principal')],
    ['Acompanham.', buscar('acompanhamentos')],
    ['Salada', buscar('salada')],
  ].filter(([, categoria]) => categoria)

  const linhas =
    preferidas.length >= 2
      ? preferidas
      : categorias
          .filter((c) => c.pratos.length)
          .slice(0, 3)
          .map((c) => [c.rotulo.split(' — ')[0], c])

  return linhas.map(([rotulo, categoria]) => ({
    rotulo,
    texto: categoria.pratos.map((p) => p.nome).join(', '),
  }))
}

/** 4.2857 → "4,3" (nota média no formato brasileiro). */
export function formatarNota(media) {
  return media == null ? '–' : media.toFixed(1).replace('.', ',')
}
