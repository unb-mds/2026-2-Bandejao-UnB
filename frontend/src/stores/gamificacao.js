import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useGamificacaoStore = defineStore('gamificacao', () => {
  const ultimosPontos = ref(null)
  const aviso = ref(null)
  const progressoDesatualizado = ref(false)
  let ultimoIdDoAviso = 0

  function registrarPontos(pontos) {
    const total = pontos?.total
    if (!Number.isInteger(total) || total < 0) {
      console.error('Bloco pontos fora do contrato.', pontos)
      return
    }
    ultimosPontos.value = {
      total,
      contribuicao: pontos.contribuicao ?? 0,
      avaliacaoLiberada: pontos.avaliacaoLiberada ?? 0,
    }
    if (total === 0) return
    ultimoIdDoAviso += 1
    aviso.value = { id: ultimoIdDoAviso, total }
    progressoDesatualizado.value = true
  }

  function fecharAviso(id = aviso.value?.id) {
    if (aviso.value?.id === id) aviso.value = null
  }

  return { ultimosPontos, aviso, progressoDesatualizado, registrarPontos, fecharAviso }
})
