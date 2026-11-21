import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, mensagemDeErro } from '@/services/apiClient'

/** Cache do cardápio da semana vigente, por campus (RF06/RF07). */
export const useCardapioStore = defineStore('cardapio', () => {
  const porCampus = ref({})
  const carregando = ref(false)
  const erro = ref(null)
  const campi = ref([])
  const campiCarregados = ref(false)
  const erroCampi = ref(null)
  const carregandoCampi = ref(false)
  const errosPorCampus = ref({})
  const carregandoPorCampus = ref({})
  let pedidoCampi = null

  function carregarCampi({ forcar = false } = {}) {
    if (campiCarregados.value && !forcar) return Promise.resolve(campi.value)
    carregandoCampi.value = true
    pedidoCampi ??= apiClient
      .get('/campi/')
      .then((lista) => {
        if (!Array.isArray(lista)) throw new Error('Resposta inesperada de GET /api/campi/.')
        campi.value = lista
        campiCarregados.value = true
        erroCampi.value = null
        return lista
      })
      .catch((falha) => {
        erroCampi.value = mensagemDeErro(falha)
        return campi.value
      })
      .finally(() => {
        pedidoCampi = null
        carregandoCampi.value = false
      })
    return pedidoCampi
  }

  function buscarCampus(id) {
    return campi.value.find((campus) => campus.id === id) ?? null
  }

  async function carregar(campusId, { forcar = false } = {}) {
    if (!campusId) return null
    if (porCampus.value[campusId] && !forcar) return porCampus.value[campusId]
    carregando.value = true
    carregandoPorCampus.value[campusId] = true
    erro.value = null
    delete errosPorCampus.value[campusId]
    try {
      const semana = await apiClient.get(`/cardapio/${campusId}/`)
      porCampus.value[campusId] = semana
      return semana
    } catch (falha) {
      erro.value = mensagemDeErro(falha)
      errosPorCampus.value[campusId] = { mensagem: erro.value, codigo: falha?.codigo ?? null }
      return null
    } finally {
      carregando.value = false
      delete carregandoPorCampus.value[campusId]
    }
  }

  function erroDe(campusId) {
    return errosPorCampus.value[campusId] ?? null
  }

  function estaCarregando(campusId) {
    return Boolean(carregandoPorCampus.value[campusId])
  }

  function semana(campusId) {
    return porCampus.value[campusId] ?? null
  }

  function refeicao(campusId, data, tipo) {
    const dia = semana(campusId)?.dias.find((d) => d.data === data)
    return dia?.refeicoes.find((r) => r.tipo === tipo) ?? null
  }

  return {
    porCampus,
    carregando,
    erro,
    campi,
    campiCarregados,
    erroCampi,
    carregandoCampi,
    carregar,
    erroDe,
    estaCarregando,
    carregarCampi,
    buscarCampus,
    semana,
    refeicao,
  }
})
