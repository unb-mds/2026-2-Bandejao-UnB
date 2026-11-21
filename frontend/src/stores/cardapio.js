import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, mensagemDeErro } from '@/services/apiClient'
import { DIETA_PADRAO } from '@/constants/dietas'
import { MENSAGEM_CAMPUS_INEXISTENTE } from '@/constants/campi'

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
  const carregandoCampi = ref(false)
  const errosPorCampus = ref({})
  const carregandoPorCampus = ref({})
  let pedidoCampi = null
  const refeicoes = ref({})
  const errosDaRefeicao = ref({})
  const carregandoDaRefeicao = ref({})
  const campiInexistentes = ref({})

  function daRefeicao(pedido) {
    return refeicoes.value[chaveDaRefeicao(pedido)] ?? null
  }

  function erroDaRefeicao(pedido) {
    return errosDaRefeicao.value[chaveDaRefeicao(pedido)] ?? null
  }

  function estaCarregandoRefeicao(pedido) {
    return Boolean(carregandoDaRefeicao.value[chaveDaRefeicao(pedido)])
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
    carregandoDaRefeicao.value[chave] = true
    delete errosDaRefeicao.value[chave]
    try {
      const resposta = await apiClient.get(`/cardapio/?${parametros}`)
      refeicoes.value[chave] = resposta
      const resolvida = { ...pedido, dia: resposta.data, refeicao: resposta.refeicao }
      refeicoes.value[chaveDaRefeicao(resolvida)] = resposta
      return resposta
    } catch (falha) {
      errosDaRefeicao.value[chave] = {
        mensagem: mensagemDeErro(falha),
        codigo: falha?.codigo ?? null,
      }
      if (falha?.status === 400 && falha.message === MENSAGEM_CAMPUS_INEXISTENTE) {
        campiInexistentes.value[pedido.campus] = true
      }
      return null
    } finally {
      delete carregandoDaRefeicao.value[chave]
    }
  }

  function campusInexistente(campusId) {
    return (
      Boolean(campiInexistentes.value[campusId]) ||
      errosPorCampus.value[campusId]?.codigo === 'campus_nao_encontrado'
    )
  }

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
    refeicoes,
    daRefeicao,
    erroDaRefeicao,
    estaCarregandoRefeicao,
    carregarRefeicao,
    campusInexistente,
    carregar,
    erroDe,
    estaCarregando,
    carregarCampi,
    buscarCampus,
    semana,
    refeicao,
  }
})
