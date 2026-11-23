import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError, apiClient, mensagemDeErro } from '@/services/apiClient'

const ehPontuacao = (valor) => Number.isInteger(valor) && valor >= 0

/** Só o que a linha pública pode ter: posição, apelido e patente (RI10, RI12). */
const linhaPublica = ({ posicao, apelido, patente }) => ({ posicao, apelido, patente })

const ehBlocoDePontos = (pontos) =>
  ehPontuacao(pontos?.total) &&
  ehPontuacao(pontos.contribuicao) &&
  ehPontuacao(pontos.avaliacaoLiberada)

export const useGamificacaoStore = defineStore('gamificacao', () => {
  const ultimosPontos = ref(null)
  const aviso = ref(null)
  const progressoDesatualizado = ref(false)
  let ultimoIdDoAviso = 0
  /** campusId → `{ campusId, semestre, linhas }` (schema RankingPublico). */
  const rankingPorCampus = ref({})
  /** campusId → 'carregando' | 'carregado' | 'nao_encontrado' | 'indisponivel' (501) | 'erro'. */
  const situacaoPorCampus = ref({})
  const erroPorCampus = ref({})

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

  function rankingDoCampus(campusId) {
    return rankingPorCampus.value[campusId] ?? null
  }

  function situacaoDoRanking(campusId) {
    return situacaoPorCampus.value[campusId] ?? null
  }

  function erroDoRanking(campusId) {
    return erroPorCampus.value[campusId] ?? null
  }

  /**
   * GET /api/ranking/{campusId}/ (público, RF27.2). Guarda só posição,
   * apelido e patente de cada linha: nunca pontos (RI12). Não pede de novo o
   * que já carregou, a não ser com `forcar`. Uma falha mantém o ranking que
   * já estava na tela. 404 e 501 não vão para o console.
   */
  async function carregarRanking(campusId, { forcar = false } = {}) {
    const situacao = situacaoDoRanking(campusId)
    if (!forcar && (situacao === 'carregado' || situacao === 'carregando')) {
      return rankingDoCampus(campusId)
    }
    situacaoPorCampus.value[campusId] = 'carregando'
    erroPorCampus.value[campusId] = null
    try {
      const resposta = await apiClient.get(`/ranking/${campusId}/`)
      if (!Array.isArray(resposta?.linhas)) {
        console.error('Ranking sem a lista de linhas.', { campusId })
        situacaoPorCampus.value[campusId] = 'erro'
        erroPorCampus.value[campusId] = 'Não foi possível carregar o ranking.'
        return null
      }
      rankingPorCampus.value[campusId] = {
        campusId: resposta.campusId,
        semestre: resposta.semestre,
        linhas: resposta.linhas.map(linhaPublica),
      }
      situacaoPorCampus.value[campusId] = 'carregado'
      return rankingDoCampus(campusId)
    } catch (falha) {
      if (falha instanceof ApiError && falha.status === 404) {
        situacaoPorCampus.value[campusId] = 'nao_encontrado'
      } else if (falha instanceof ApiError && falha.status === 501) {
        situacaoPorCampus.value[campusId] = 'indisponivel'
      } else {
        console.error('Falha ao carregar o ranking:', falha)
        situacaoPorCampus.value[campusId] = 'erro'
        erroPorCampus.value[campusId] = mensagemDeErro(falha)
      }
      return null
    }
  }

  function limpar() {
    ultimosPontos.value = null
    aviso.value = null
    progressoDesatualizado.value = false
  }

  return {
    ultimosPontos,
    aviso,
    progressoDesatualizado,
    registrarPontos,
    fecharAviso,
    limpar,
    rankingDoCampus,
    situacaoDoRanking,
    erroDoRanking,
    carregarRanking,
  }
})

export function repassarPontos(pontos, origem) {
  try {
    useGamificacaoStore().registrarPontos(pontos)
  } catch (falha) {
    console.error(`Falha ao registrar os pontos ${origem}.`, falha)
  }
}
