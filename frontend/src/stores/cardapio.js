import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, mensagemDeErro } from '@/services/apiClient'
import { DIETA_PADRAO } from '@/constants/dietas'

const chaveDaRefeicao = ({ campus, dia, refeicao, marcadores = [], dieta = DIETA_PADRAO }) =>
  JSON.stringify([campus, dia ?? null, refeicao ?? null, [...marcadores].sort(), dieta])

/** Cache do cardápio da semana vigente, por campus (RF06/RF07). */
export const useCardapioStore = defineStore('cardapio', () => {
  const porCampus = ref({})
  const carregando = ref(false)
  const erro = ref(null)
  const campi = ref([])
  const campiCarregados = ref(false)
  const erroCampi = ref(null)
  let carregandoCampi = null
  const refeicoes = ref({})
  const carregandoRefeicao = ref(false)
  const erroRefeicao = ref(null)

  function daRefeicao(pedido) {
    return refeicoes.value[chaveDaRefeicao(pedido)] ?? null
  }

  async function carregarRefeicao(pedido, { forcar = false } = {}) {
    if (!pedido.campus) return null
    const chave = chaveDaRefeicao(pedido)
    if (refeicoes.value[chave] && !forcar) return refeicoes.value[chave]
    const parametros = new URLSearchParams({ campus: String(pedido.campus) })
    if (pedido.dia) parametros.set('dia', pedido.dia)
    if (pedido.refeicao) parametros.set('refeicao', pedido.refeicao)
    if (pedido.marcadores?.length) parametros.set('marcadores', pedido.marcadores.join(','))
    if (pedido.dieta && pedido.dieta !== DIETA_PADRAO) parametros.set('dieta', pedido.dieta)
    carregandoRefeicao.value = true
    erroRefeicao.value = null
    try {
      const resposta = await apiClient.get(`/cardapio/?${parametros}`)
      refeicoes.value[chave] = resposta
      const resolvida = { ...pedido, dia: resposta.data, refeicao: resposta.refeicao }
      refeicoes.value[chaveDaRefeicao(resolvida)] = resposta
      return resposta
    } catch (falha) {
      erroRefeicao.value = mensagemDeErro(falha)
      return null
    } finally {
      carregandoRefeicao.value = false
    }
  }

  function carregarCampi({ forcar = false } = {}) {
    if (campiCarregados.value && !forcar) return Promise.resolve(campi.value)
    carregandoCampi ??= apiClient
      .get('/campi/')
      .then((lista) => {
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
        carregandoCampi = null
      })
    return carregandoCampi
  }

  function buscarCampus(id) {
    return campi.value.find((campus) => campus.id === id) ?? null
  }

  async function carregar(campusId, { forcar = false } = {}) {
    if (!campusId) return null
    if (porCampus.value[campusId] && !forcar) return porCampus.value[campusId]
    carregando.value = true
    erro.value = null
    try {
      const semana = await apiClient.get(`/cardapio/${campusId}/`)
      porCampus.value[campusId] = semana
      return semana
    } catch (falha) {
      erro.value = mensagemDeErro(falha)
      return null
    } finally {
      carregando.value = false
    }
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
    refeicoes,
    carregandoRefeicao,
    erroRefeicao,
    daRefeicao,
    carregarRefeicao,
    carregar,
    carregarCampi,
    buscarCampus,
    semana,
    refeicao,
  }
})
