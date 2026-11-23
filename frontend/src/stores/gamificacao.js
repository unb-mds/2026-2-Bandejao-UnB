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

/**
 * 501 quer dizer que o backend não tem a regra: vira `indisponivel`, sem
 * mensagem de erro, para a tela mostrar "ainda não disponível". Desde a BE-16
 * e a BE-17, as três rotas respondem, e o 501 vale só como defesa.
 */
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
  /** Muda a cada `limpar()`: o que chega de um pedido de antes do logout é descartado. */
  let geracao = 0

  /**
   * GET /api/gamificacao/progresso/. Sem `forcar`, usa o que já está em dia ou
   * o pedido em andamento. Com dados na tela, recarrega sem voltar a
   * "carregando" e, se falhar, mantém os dados e os marca como desatualizados.
   * Só grava a resposta do pedido mais novo e da mesma `geracao`.
   */
  function carregarProgresso({ forcar = false } = {}) {
    const emDia = progresso.value.situacao === 'carregado' && !progressoDesatualizado.value
    if (!forcar && emDia) return Promise.resolve(progresso.value)
    if (!forcar && pedidoDoProgresso) return pedidoDoProgresso
    const geracaoDoPedido = geracao
    if (!progresso.value.dados) progresso.value = { situacao: 'carregando', dados: null, erro: null }
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
        const atual = pedidoDoProgresso === promessa
        if (atual) pedidoDoProgresso = null
        if (!atual || geracaoDoPedido !== geracao) return progresso.value
        if (estado.situacao === 'carregado') {
          progresso.value = estado
          progressoDesatualizado.value = false
        } else if (progresso.value.dados) {
          progressoDesatualizado.value = true
        } else {
          progresso.value = estado
        }
        return progresso.value
      })
    pedidoDoProgresso = promessa
    return promessa
  }

  function rankingDe(campusId) {
    return rankings.value[Number(campusId)] ?? null
  }

  /**
   * GET /api/ranking/{campusId}/, com cache por campus. A guarda
   * `pedidosDeRanking.get(campusId) === promessa` impede que uma resposta
   * antiga sobrescreva a de um pedido com `forcar` feito depois.
   */
  function carregarRanking(id, { forcar = false } = {}) {
    const campusId = Number(id)
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

  /**
   * POST/DELETE /api/gamificacao/adesao/ (RF27.1). Com o 204, grava o novo
   * `participaRanking` na hora, descarta os comentários guardados e recarrega
   * o progresso e os rankings já abertos. Um segundo toque enquanto o primeiro
   * não termina é ignorado.
   */
  async function alterarAdesao(participar) {
    if (alterandoAdesao.value) return { desfecho: 'ignorado' }
    const geracaoDoPedido = geracao
    alterandoAdesao.value = true
    erroDaAdesao.value = null
    try {
      if (participar) await apiClient.post('/gamificacao/adesao/')
      else await apiClient.delete('/gamificacao/adesao/')
      if (geracaoDoPedido !== geracao) return { desfecho: 'ignorado' }
      useAvaliacoesStore().limparCache()
      if (progresso.value.dados) {
        progresso.value = {
          ...progresso.value,
          dados: { ...progresso.value.dados, participaRanking: participar },
        }
      }
      await Promise.all([
        carregarProgresso({ forcar: true }),
        ...Object.keys(rankings.value).map((id) => carregarRanking(Number(id), { forcar: true })),
      ])
      return { desfecho: 'ok' }
    } catch (falha) {
      const mensagem = mensagemDeErro(falha)
      if (geracaoDoPedido === geracao) erroDaAdesao.value = mensagem
      return { desfecho: 'erro', mensagem }
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
    pedidoDoProgresso = null
    rankings.value = {}
    pedidosDeRanking.clear()
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
