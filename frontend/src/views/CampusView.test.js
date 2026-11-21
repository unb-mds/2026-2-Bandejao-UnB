import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

const SEGUNDA = (hora, minuto = 0) => new Date(2026, 8, 28, hora, minuto)
const COORDENADAS = { latitude: -15.7631234, longitude: -47.8701234 }

let pinia
async function montarEm(caminho) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

function simularGps({ responderNaHora = true } = {}) {
  let responder = () => {}
  const getCurrentPosition = vi.fn((ok) => {
    const ler = () => ok({ coords: { ...COORDENADAS, accuracy: 15 }, timestamp: Date.now() })
    if (responderNaHora) ler()
    else responder = ler
  })
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn(async () => ({ state: 'granted' })) },
    geolocation: { getCurrentPosition },
  })
  return { responder: () => responder() }
}

async function entrarComAvisoAceito() {
  const auth = useAuthStore()
  await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  await auth.registrarCienciaPrivacidade()
}

const checkinsEnviados = (post) =>
  post.mock.calls.filter(([caminho]) => caminho === '/checkins/').map(([, corpo]) => corpo)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA(12))
  vi.stubGlobal('isSecureContext', true)
  localStorage.clear()
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('CampusView (FE-07, front 3a.2)', () => {
  it('mostra o nome do campus vindo do GET /api/campi/', async () => {
    const { wrapper } = await montarEm('/campus/3')

    await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Gama'))
  })

  it('AvisoExecutivo só no Darcy Ribeiro (RF20.4)', async () => {
    const darcy = await montarEm('/campus/1')
    await vi.waitFor(() => expect(darcy.wrapper.find('h1').text()).toBe('Darcy Ribeiro'))
    expect(darcy.wrapper.find('[data-teste="aviso-executivo"]').exists()).toBe(true)
    darcy.wrapper.unmount()

    const gama = await montarEm('/campus/3')
    await vi.waitFor(() => expect(gama.wrapper.find('h1').text()).toBe('Gama'))
    expect(gama.wrapper.find('[data-teste="aviso-executivo"]').exists()).toBe(false)
  })

  it('cardápio e fila na mesma tela', async () => {
    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(wrapper.text()).toContain('Fila do RU')
    expect(wrapper.text()).toContain('Entre para fazer check-in')
  })

  it('uma seção falhando não derruba a outra', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho.startsWith('/cardapio/')
        ? Promise.reject(new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }))
        : getOriginal(caminho, opcoes),
    )

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() =>
      expect(wrapper.text()).toContain('Não foi possível carregar o cardápio'),
    )
    expect(wrapper.text()).toContain('Fila do RU')
    expect(wrapper.text()).toContain('Entre para fazer check-in')
  })

  it('a lista de campi falhando não esconde o cardápio', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/campi/'
        ? Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
        : getOriginal(caminho, opcoes),
    )

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(wrapper.text()).not.toContain('Campus não encontrado')
  })

  it('refeição encerrada: RefeicaoEncerrada no lugar do check-in (RN05)', async () => {
    vi.setSystemTime(SEGUNDA(20))

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true),
    )
    expect(wrapper.text()).not.toContain('Entre para fazer check-in')
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(false)
  })

  it('o check-in usa o campus da tela e a refeição selecionada', async () => {
    simularGps()
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true),
    )

    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    expect(checkinsEnviados(post)).toEqual([
      { campus: 1, tipoRefeicao: 'almoco', coordenadas: COORDENADAS },
    ])
    await vi.waitFor(() => expect(wrapper.text()).toContain('Check-in confirmado'))
  })

  it('trocar a refeição durante a leitura do GPS: nenhum POST com a refeição nova', async () => {
    const gps = simularGps({ responderNaHora: false })
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true),
    )
    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    const preferencias = usePreferenciasStore()
    preferencias.selecionar(preferencias.dataSelecionada, 'jantar')
    await flushPromises()
    gps.responder()
    await flushPromises()

    for (const corpo of checkinsEnviados(post)) {
      expect(corpo).toMatchObject({ campus: 1, tipoRefeicao: 'almoco' })
    }
    expect(checkinsEnviados(post).some((corpo) => corpo.tipoRefeicao === 'jantar')).toBe(false)
    expect(wrapper.text()).not.toContain('Check-in confirmado')
  })
})
