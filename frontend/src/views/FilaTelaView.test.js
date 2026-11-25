import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'
import { apiClient, ApiError } from '@/services/apiClient'

const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)

async function montarFila(campus = 1, selecao = null) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (campus) usePreferenciasStore().escolherCampus(campus)
  if (selecao) usePreferenciasStore().selecionar(...selecao)
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push('/fila')
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  localStorage.clear()
  reiniciarSimulacao()
})

enableAutoUnmount(afterEach)

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('FilaTelaView: a tela "Fila do RU" (RF12, RF13)', () => {
  it('título, campus lembrado e a previsão do almoço de hoje', async () => {
    const { wrapper } = await montarFila(1)

    expect(wrapper.get('h1').text()).toBe('Fila do RU')
    await vi.waitFor(() => expect(wrapper.get('header').text()).toContain('Darcy Ribeiro'))
    await vi.waitFor(() =>
      expect(wrapper.find('[aria-labelledby="titulo-previsao"]').text()).toContain('Almoço'),
    )
  })

  it('sem login: o convite do check-in, com a refeição de agora', async () => {
    const { wrapper } = await montarFila(1)

    await vi.waitFor(() =>
      expect(wrapper.get('main').text()).toContain('Entre para fazer check-in'),
    )
    expect(wrapper.get('main').text()).toContain('Check-in · Almoço')
  })

  it('não carrega o cardápio: é a tela da fila, só', async () => {
    const get = vi.spyOn(apiClient, 'get')
    const { wrapper } = await montarFila(1)
    expect(wrapper.find('[aria-labelledby="titulo-cardapio"]').exists()).toBe(false)
    expect(get.mock.calls.some(([caminho]) => caminho.startsWith('/cardapio/'))).toBe(false)
  })

  it.each(['2026-09-27', '2026-09-28', '2026-09-29'])(
    'ignora a seleção do cardápio de %s', async (data) => {
      vi.setSystemTime(new Date(2026, 8, 28, 18, 0))
      const { wrapper } = await montarFila(1, [data, 'almoco'])
      await vi.waitFor(() => expect(wrapper.get('#titulo-previsao').text()).toContain('Jantar'))
      expect(wrapper.get('#titulo-checkin').text()).toContain('Jantar')
      expect(wrapper.get('#titulo-previsao').text()).toContain('hoje')
    },
  )

  it('esquece campus inexistente e oferece nova escolha', async () => {
    const { wrapper } = await montarFila(99)
    await vi.waitFor(() => expect(wrapper.text()).toContain('Campus não encontrado'))
    expect(wrapper.text()).toContain('Escolher o campus')
    expect(usePreferenciasStore().campusId).toBeNull()
  })

  it('permite tentar novamente após falha nos campi', async () => {
    const original = apiClient.get.bind(apiClient)
    let falhar = true
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/campi/' && falhar
        ? Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
        : original(caminho, opcoes),
    )
    const { wrapper } = await montarFila(1)
    await vi.waitFor(() => expect(wrapper.get('[data-teste="falha-campi"]').text()).toContain('Sem internet.'))
    falhar = false
    await wrapper.get('[data-teste="falha-campi"] button').trigger('click')
    await vi.waitFor(() => expect(wrapper.get('#titulo-checkin').text()).toContain('Almoço'))
  })

  it('o botão de voltar leva à tela do campus', async () => {
    const { wrapper, router } = await montarFila(1)

    await wrapper.get('header button[aria-label="Voltar"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('campus-tela'))
    expect(router.currentRoute.value.params.campusId).toBe('1')
  })
})
