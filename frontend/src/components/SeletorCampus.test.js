import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'
import SeletorCampus from './SeletorCampus.vue'

const AGORA = new Date(2026, 8, 28, 12, 0)

let pinia
async function montar() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push('/campus')
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  await vi.waitFor(() => expect(wrapper.find('h1').text()).toContain('Qual campus'))
  return { wrapper, router }
}

function campiComo(...respostas) {
  const getOriginal = apiClient.get.bind(apiClient)
  const fila = [...respostas]
  return vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
    if (caminho !== '/campi/') return getOriginal(caminho, opcoes)
    const proxima = fila.shift()
    return proxima ? proxima() : getOriginal(caminho, opcoes)
  })
}

function adiada() {
  let resolver
  let rejeitar
  const promessa = new Promise((ok, falha) => {
    resolver = ok
    rejeitar = falha
  })
  return { promessa, resolver, rejeitar }
}

const semConexao = () =>
  Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
const pedidosDeCampi = (get) => get.mock.calls.filter(([caminho]) => caminho === '/campi/')
const botaoTentar = (wrapper) =>
  wrapper.findAll('button').find((botao) => botao.text() === 'Tentar novamente')

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(AGORA)
  localStorage.clear()
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('SeletorCampus (FE-07)', () => {
  it('mostra "Carregando campi…" enquanto a lista não chega', async () => {
    campiComo(() => new Promise(() => {}))

    const { wrapper } = await montar()

    expect(wrapper.text()).toContain('Carregando campi…')
  })

  it('lista os campi do GET /api/campi/', async () => {
    const { wrapper } = await montar()

    await vi.waitFor(() => expect(wrapper.findAll('.campus')).toHaveLength(5))
    expect(wrapper.text()).toContain('Darcy Ribeiro')
    expect(wrapper.text()).toContain('Fazenda Água Limpa')
  })

  it('falha: mostra o erro e "Tentar novamente" carrega de novo, com retorno na tela', async () => {
    const segunda = adiada()
    const get = campiComo(semConexao, () => segunda.promessa)

    const { wrapper } = await montar()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Não foi possível carregar os campi.'))
    expect(wrapper.text()).toContain('Sem internet.')

    await botaoTentar(wrapper).trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Carregando campi…')
    expect(wrapper.text()).not.toContain('Não foi possível carregar os campi.')

    segunda.resolver([{ id: 3, nome: 'Gama' }])
    await flushPromises()

    expect(wrapper.findAll('.campus')).toHaveLength(1)
    expect(pedidosDeCampi(get)).toHaveLength(2)
  })

  it('falha de novo: o erro volta depois do "Carregando campi…"', async () => {
    const get = campiComo(semConexao, semConexao)

    const { wrapper } = await montar()
    await vi.waitFor(() => expect(botaoTentar(wrapper)).toBeTruthy())

    await botaoTentar(wrapper).trigger('click')
    await flushPromises()

    expect(pedidosDeCampi(get)).toHaveLength(2)
    expect(wrapper.text()).toContain('Não foi possível carregar os campi.')
    expect(wrapper.text()).not.toContain('Carregando campi…')
  })

  it('lista vazia: "Nenhum campus disponível no momento."', async () => {
    campiComo(() => Promise.resolve([]))

    const { wrapper } = await montar()

    await vi.waitFor(() =>
      expect(wrapper.text()).toContain('Nenhum campus disponível no momento.'),
    )
  })

  it('destaca o campus lembrado', async () => {
    usePreferenciasStore().escolherCampus(3)

    const { wrapper } = await montar()

    await vi.waitFor(() => expect(wrapper.findAll('.campus')).toHaveLength(5))
    const atuais = wrapper.findAll('.campus--atual')
    expect(atuais).toHaveLength(1)
    expect(atuais[0].text()).toContain('Gama')
  })

  it('escolher um campus lembra o id e abre a tela dele', async () => {
    const { wrapper, router } = await montar()
    await vi.waitFor(() => expect(wrapper.findAll('.campus')).toHaveLength(5))

    const gama = wrapper.findAll('.campus').find((botao) => botao.text().includes('Gama'))
    await gama.trigger('click')

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('campus-tela'))
    expect(usePreferenciasStore().campusId).toBe(3)
    expect(router.currentRoute.value).toMatchObject({
      name: 'campus-tela',
      params: { campusId: '3' },
    })
  })
})

/** Variante compacta, dentro de outra tela (RankingView, FE-13). */
describe('SeletorCampus compacto', () => {
  async function montarCompacto(selecionado = 1) {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push('/campus')
    const wrapper = mount(SeletorCampus, {
      props: { compacto: true, selecionado },
      global: { plugins: [pinia, router] },
      attachTo: document.body,
    })
    await flushPromises()
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-teste="seletor-campus-opcao"]')).toHaveLength(5),
    )
    return { wrapper, router }
  }

  it('lista os campi como opções, sem o cabeçalho da tela de escolha', async () => {
    const { wrapper } = await montarCompacto()

    expect(wrapper.find('h1').exists()).toBe(false)
    expect(wrapper.text()).toContain('Darcy Ribeiro')
    expect(wrapper.text()).toContain('Planaltina')
  })

  it('marca o campus selecionado com aria-pressed', async () => {
    const { wrapper } = await montarCompacto(3)

    const marcadas = wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .filter((b) => b.attributes('aria-pressed') === 'true')
    expect(marcadas.map((b) => b.text())).toEqual(['Gama'])
  })

  it('escolher avisa a tela (evento "escolher"), sem navegar nem trocar o campus lembrado', async () => {
    const { wrapper, router } = await montarCompacto(1)
    usePreferenciasStore().escolherCampus(1)

    const gama = wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .find((b) => b.text() === 'Gama')
    await gama.trigger('click')
    await flushPromises()

    expect(wrapper.emitted('escolher')).toEqual([[3]])
    expect(router.currentRoute.value.name).toBe('campus')
    expect(usePreferenciasStore().campusId).toBe(1)
  })
})
