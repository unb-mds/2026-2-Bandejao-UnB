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
 * Dias das abas do cardápio (RF07.1): de segunda a domingo da semana do
 * calendário; o domingo pertence à semana da segunda anterior. Coincide com a
 * semana do PDF no backend (`semana_inicio` + 6 dias). Campi sem refeição no
 * dia respondem com `semServico` e a tela mostra o estado de sem serviço.
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
  // Minúsculas e sem acento: os PDFs trazem "PRATO PRINCIPAL PADRÃO" ou "PADRAO".
  const normalizar = (texto) =>
    texto
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
  const comPratos = categorias.filter((c) => c.pratos.length)
  const buscar = (trecho) => comPratos.find((c) => normalizar(c.nome).startsWith(trecho))
  // O padrão é a categoria sem dieta no nome ("Prato principal") ou com "padrão";
  // as vegetarianas podem vir antes dela na lista.
  const pratoPrincipal =
    comPratos.find((c) => {
      const nome = normalizar(c.nome)
      return (
        nome.startsWith('prato principal') &&
        (nome.includes('padrao') || nome.trim() === 'prato principal')
      )
    }) ?? buscar('prato principal')
  const preferidas = [
    ['Prato principal', pratoPrincipal],
    ['Acompanham.', buscar('acompanhamento')],
    ['Salada', buscar('salada')],
  ].filter(([, categoria]) => categoria)

  const linhas =
    preferidas.length >= 2
      ? preferidas
      : categorias
          .filter((c) => c.pratos.length)
          .slice(0, 3)
          .map((c) => [c.nome.split(' — ')[0], c])

  return linhas.map(([rotulo, categoria]) => ({
    rotulo,
    texto: categoria.pratos.map((p) => p.descricao).join(', '),
  }))
}

/**
 * Destaque da refeição no desktop (FE-23): o primeiro prato principal
 * compatível com os marcadores evitados (RF08), com o padrão antes das outras
 * linhas, e os acompanhamentos e a salada compatíveis no resumo. A dieta
 * (RF09) já vem aplicada pela API. Sem prato compatível, ou com a informação
 * de alérgenos indisponível enquanto a pessoa evita algum marcador, não há
 * destaque: ele não pode sugerir um prato que a lista abaixo desaconselha.
 * Refeição sem prato principal (café da manhã): a primeira categoria com prato.
 */
export function destaqueDaRefeicao(categorias, { semAlergenos = false, evitando = false } = {}) {
  if (semAlergenos && evitando) return null
  const normalizar = (texto) =>
    texto
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
  const compativeis = (categoria) => categoria.pratos.filter((p) => !p.contemMarcadorSelecionado)
  const principais = categorias.filter((c) => normalizar(c.nome).startsWith('prato principal'))
  const ehPadrao = (c) => {
    const nome = normalizar(c.nome)
    return nome.includes('padrao') || nome.trim() === 'prato principal'
  }
  const candidatas = principais.length
    ? [...principais.filter(ehPadrao), ...principais.filter((c) => !ehPadrao(c))]
    : categorias
  const escolhida = candidatas.find((c) => compativeis(c).length)
  if (!escolhida) return null

  const resumo = principais.length
    ? categorias
        .filter((c) => /^(acompanhamento|salada)/.test(normalizar(c.nome)))
        .map((c) =>
          compativeis(c)
            .map((p) => p.descricao)
            .join(', '),
        )
        .filter(Boolean)
        .join(' · ')
    : ''
  return { prato: compativeis(escolhida)[0].descricao, resumo }
}

/** 4.2857 → "4,3" (nota média no formato brasileiro). */
export function formatarNota(media) {
  return media == null ? '–' : media.toFixed(1).replace('.', ',')
}
