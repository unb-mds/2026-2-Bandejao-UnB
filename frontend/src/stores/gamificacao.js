import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient, mensagemDeErro } from '@/services/apiClient'
import { IDS_PATENTES } from '@/constants/patentes'
import { useAvaliacoesStore } from '@/stores/avaliacoes'

const ehPontuacao = (valor) => Number.isInteger(valor) && valor >= 0

const ehBlocoDePontos = (pontos) =>
  ehPontuacao(pontos?.total) &&
  ehPontuacao(pontos.contribuicao) &&
  ehPontuacao(pontos.avaliacaoLiberada)

const CAMPOS_NUMERICOS_DO_PROGRESSO = [
  'pontosTotais',
  'faltaParaProxima',
  'sequencia',
  'diasNaSemana',
  'minimoDias',
]

const ehProgresso = (resposta) =>
  IDS_PATENTES.includes(resposta?.patente) &&
  CAMPOS_NUMERICOS_DO_PROGRESSO.every((campo) => ehPontuacao(resposta[campo])) &&
  typeof resposta.participaRanking === 'boolean'

const ehLinhaDoRanking = (linha) =>
  Number.isInteger(linha?.posicao) &&
  linha.posicao > 0 &&
  typeof linha.apelido === 'string' &&
  IDS_PATENTES.includes(linha.patente)

const ehRanking = (resposta, campusId) =>
  resposta?.campusId === campusId &&
  typeof resposta.semestre === 'string' &&
  Array.isArray(resposta.linhas) &&
  resposta.linhas.every(ehLinhaDoRanking)

function estadoDaFalha(falha) {
  if (falha?.status === 501) return { situacao: 'indisponivel', dados: null, erro: null }
  return {
    situacao: 'erro',
    dados: null,
    erro: { mensagem: mensagemDeErro(falha), codigo: falha?.codigo ?? null },
  }
}

export const useGamificacaoStore = defineStore('gamificacao', () => {
  const ultimosPontos = ref(null)
  const aviso = ref(null)
  const progressoDesatualizado = ref(false)
  let ultimoIdDoAviso = 0
  const progresso = ref({ situacao: null, dados: null, erro: null })
  const rankings = ref({})
  const alterandoAdesao = ref(false)
  const erroDaAdesao = ref(null)
  let pedidoDoProgresso = null
  const pedidosDeRanking = new Map()
  let geracao = 0

  function carregarProgresso({ forcar = false } = {}) {
    const emDia = progresso.value.situacao === 'carregado' && !progressoDesatualizado.value
    if (!forcar && emDia) return Promise.resolve(progresso.value)
    if (!forcar && pedidoDoProgresso) return pedidoDoProgresso
    const geracaoDoPedido = geracao
    progresso.value = { ...progresso.value, situacao: 'carregando', erro: null }
    const promessa = apiClient
      .get('/gamificacao/progresso/')
      .then((resposta) => {
        if (!ehProgresso(resposta)) {
          throw new Error('Resposta inesperada de GET /api/gamificacao/progresso/.', {
            cause: resposta,
          })
        }
        return { situacao: 'carregado', dados: resposta, erro: null }
      })
      .catch(estadoDaFalha)
      .then((estado) => {
        if (pedidoDoProgresso === promessa) pedidoDoProgresso = null
        if (geracaoDoPedido === geracao) {
          progresso.value = estado
          if (estado.situacao === 'carregado') progressoDesatualizado.value = false
        }
        return progresso.value
      })
    pedidoDoProgresso = promessa
    return promessa
  }

  function rankingDe(campusId) {
    return rankings.value[campusId] ?? null
  }

  function carregarRanking(campusId, { forcar = false } = {}) {
    const atual = rankings.value[campusId]
    if (!forcar && atual?.situacao === 'carregado') return Promise.resolve(atual)
    if (!forcar && pedidosDeRanking.has(campusId)) return pedidosDeRanking.get(campusId)
    rankings.value[campusId] = { ...atual, situacao: 'carregando', erro: null }
    const promessa = apiClient
      .get(`/ranking/${campusId}/`)
      .then((resposta) => {
        if (!ehRanking(resposta, campusId)) {
          throw new Error(`Resposta inesperada de GET /api/ranking/${campusId}/.`, {
            cause: resposta,
          })
        }
        return { situacao: 'carregado', dados: resposta, erro: null }
      })
      .catch(estadoDaFalha)
      .then((estado) => {
        if (pedidosDeRanking.get(campusId) === promessa) {
          rankings.value[campusId] = estado
          pedidosDeRanking.delete(campusId)
        }
        return estado
      })
    pedidosDeRanking.set(campusId, promessa)
    return promessa
  }

  async function alterarAdesao(participar) {
    if (alterandoAdesao.value) return { desfecho: 'ignorado' }
    alterandoAdesao.value = true
    erroDaAdesao.value = null
    try {
      if (participar) await apiClient.post('/gamificacao/adesao/')
      else await apiClient.delete('/gamificacao/adesao/')
      useAvaliacoesStore().limparCache()
      await Promise.all([
        carregarProgresso({ forcar: true }),
        ...Object.keys(rankings.value).map((id) => carregarRanking(Number(id), { forcar: true })),
      ])
      return { desfecho: 'ok' }
    } catch (falha) {
      erroDaAdesao.value = mensagemDeErro(falha)
      return { desfecho: 'erro', mensagem: erroDaAdesao.value }
    } finally {
      alterandoAdesao.value = false
    }
  }

  /**
   * Recebe o bloco `pontos` de uma resposta de check-in ou de avaliação
   * (RF24.2). Guarda os três campos do contrato e, com `total > 0`, abre um
   * aviso novo para o `PontosAviso`, mesmo que o total seja igual ao do
   * anterior. Um bloco fora do contrato é ignorado e vai para o console.
   */
  function registrarPontos(pontos) {
    if (!ehBlocoDePontos(pontos)) {
      console.error('Bloco pontos fora do contrato.', pontos)
      return
    }
    const { total, contribuicao, avaliacaoLiberada } = pontos
    ultimosPontos.value = { total, contribuicao, avaliacaoLiberada }
    if (total === 0) return
    ultimoIdDoAviso += 1
    aviso.value = { id: ultimoIdDoAviso, total }
    progressoDesatualizado.value = true
  }

  /**
   * Fecha o aviso aberto. Com `id`, só fecha se ele ainda for o aviso atual:
   * o temporizador de um aviso antigo não pode fechar um mais novo.
   */
  function fecharAviso(id = aviso.value?.id) {
    if (aviso.value?.id === id) aviso.value = null
  }

  function limpar() {
    geracao++
    ultimosPontos.value = null
    aviso.value = null
    progressoDesatualizado.value = false
    progresso.value = { situacao: null, dados: null, erro: null }
    erroDaAdesao.value = null
  }

  return {
    ultimosPontos,
    aviso,
    progressoDesatualizado,
    progresso,
    rankings,
    alterandoAdesao,
    erroDaAdesao,
    registrarPontos,
    fecharAviso,
    limpar,
    carregarProgresso,
    rankingDe,
    carregarRanking,
    alterarAdesao,
  }
})

export function repassarPontos(pontos, origem) {
  try {
    useGamificacaoStore().registrarPontos(pontos)
  } catch (falha) {
    console.error(`Falha ao registrar os pontos ${origem}.`, falha)
  }
}
