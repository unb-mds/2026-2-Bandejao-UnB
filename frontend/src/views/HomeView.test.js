import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

const DOMINGO_MEIO_DIA = new Date(2026, 9, 4, 12, 0)

async function montarHome(campusId) {
  localStorage.setItem('bandejao:preferencias', JSON.stringify({ campusId }))
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push('/inicio')
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  await vi.waitFor(() =>
    expect(wrapper.find('.cartao-hoje').text()).not.toContain('Carregando cardápio'),
  )
  return wrapper
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(DOMINGO_MEIO_DIA)
  localStorage.clear()
  reiniciarSimulacao()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('HomeView: cartão "Cardápio de hoje" no domingo (#229)', () => {
  it('campus que serve no domingo (Darcy): mostra a refeição de domingo', async () => {
    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.find('.hoje-linhas').exists()).toBe(true)
    expect(cartao.text()).toContain('Almoço')
    expect(cartao.text()).not.toContain('Não há refeições servidas hoje')
  })

  it('campus sem serviço no domingo (Gama): mostra que não há refeições hoje', async () => {
    const wrapper = await montarHome(3)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.text()).toContain('Não há refeições servidas hoje neste campus.')
    expect(cartao.find('.hoje-linhas').exists()).toBe(false)
  })
})
