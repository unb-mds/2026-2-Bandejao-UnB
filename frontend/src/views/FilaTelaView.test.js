import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)

async function montarFila(campus = 1) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (campus) usePreferenciasStore().escolherCampus(campus)
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
    const { wrapper } = await montarFila(1)

    expect(wrapper.find('[aria-labelledby="titulo-cardapio"]').exists()).toBe(false)
  })

  it('o botão de voltar leva à tela do campus', async () => {
    const { wrapper, router } = await montarFila(1)

    await wrapper.get('header button[aria-label="Voltar"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('campus-tela'))
    expect(router.currentRoute.value.params.campusId).toBe('1')
  })
})
