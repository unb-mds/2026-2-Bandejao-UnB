import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { reiniciarAvisoLocalizacaoParaTestes } from '@/composables/avisoLocalizacao'
import App from '@/App.vue'

/** Integração: o AvisoLocalizacao montado pelo App e aberto pelo menu da Início. */

// Segunda-feira, 28/09/2026, 12h.
const AGORA = new Date(2026, 8, 28, 12, 0)

function simularNavegador(estado = 'prompt') {
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn(async () => ({ state: estado })) },
    geolocation: { getCurrentPosition: vi.fn() },
  })
}

let wrapper
async function montarEm(caminho, { campus = 1, adiado = false } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const preferencias = usePreferenciasStore()
  preferencias.escolherCampus(campus)
  if (adiado) preferencias.adiarAvisoLocalizacao()

  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

const avisoAberto = () => wrapper.find('dialog.aviso-localizacao').attributes('open') !== undefined

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(AGORA)
  localStorage.clear()
  reiniciarSimulacao()
  reiniciarAvisoLocalizacaoParaTestes()
})

afterEach(() => {
  wrapper?.unmount()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('AvisoLocalizacao no App', () => {
  it('aparece por cima da tela no primeiro acesso', async () => {
    simularNavegador()
    await montarEm('/inicio')

    expect(avisoAberto()).toBe(true)
    expect(wrapper.text()).toContain('Usar sua localização?')
  })

  it('"Usar minha localização" no menu da Início abre o aviso de novo', async () => {
    simularNavegador()
    await montarEm('/inicio', { adiado: true })
    expect(avisoAberto()).toBe(false)

    await vi.waitFor(() => expect(wrapper.find('button[aria-expanded]').exists()).toBe(true))
    await wrapper.find('button[aria-expanded]').trigger('click')
    await wrapper
      .findAll('[role="menuitem"]')
      .find((item) => item.text().includes('Usar minha localização'))
      .trigger('click')
    await flushPromises()

    expect(avisoAberto()).toBe(true)
  })
})
