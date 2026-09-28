import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient } from '@/services/apiClient'

const chaveRefeicao = ({ campus, data, refeicao }) => `${campus}|${data}|${refeicao}`

/** Avaliações das refeições e resumo semanal por campus (RF15). */
export const useAvaliacoesStore = defineStore('avaliacoes', () => {
  const porRefeicao = ref({})
  const resumoPorCampus = ref({})
  const erro = ref(null)

  function daRefeicao(alvo) {
    return porRefeicao.value[chaveRefeicao(alvo)] ?? null
  }

  async function carregar(alvo) {
    erro.value = null
    const parametros = new URLSearchParams(alvo).toString()
    try {
      porRefeicao.value[chaveRefeicao(alvo)] = await apiClient.get(`/avaliacoes/?${parametros}`)
    } catch (falha) {
      erro.value = falha.message
    }
    return daRefeicao(alvo)
  }

  async function carregarResumo(campus) {
    try {
      resumoPorCampus.value[campus] = await apiClient.get(`/avaliacoes/resumo/?campus=${campus}`)
    } catch (falha) {
      erro.value = falha.message
    }
    return resumoPorCampus.value[campus] ?? null
  }

  /** Envia (ou edita) a avaliação do usuário e atualiza média e lista. */
  async function enviar(alvo, nota, comentario) {
    const resposta = await apiClient.post('/avaliacoes/', { ...alvo, nota, comentario })
    await Promise.all([carregar(alvo), carregarResumo(alvo.campus)])
    return resposta
  }

  /** Após login/logout, a "minha avaliação" de cada refeição muda. */
  function limparCache() {
    porRefeicao.value = {}
  }

  return {
    porRefeicao,
    resumoPorCampus,
    erro,
    daRefeicao,
    carregar,
    carregarResumo,
    enviar,
    limparCache,
  }
})
