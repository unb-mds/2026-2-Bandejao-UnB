import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { useAuthStore } from '@/stores/auth'
import App from '@/App.vue'

const DOMINGO_MEIO_DIA = new Date(2026, 9, 4, 12, 0)

let router

async function montarHome(campusId, { logado = false } = {}) {
  localStorage.setItem(
    'bandejao:preferencias',
    JSON.stringify({ campusId, avisoLocalizacaoAdiado: true }),
  )
  const pinia = createPinia()
  setActivePinia(pinia)
  if (logado) await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  router = createRouter({ history: createMemoryHistory(), routes })
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

describe('HomeView: "Sair da conta" no menu (RF03.3)', () => {
  async function clicarEmSair(wrapper) {
    await wrapper.get('.avatar').trigger('click')
    const itens = wrapper.findAll('[role="menuitem"]')
    await itens.find((item) => item.text() === 'Sair da conta').trigger('click')
    await flushPromises()
  }

  it('servidor confirma: sai da conta e continua na Início, sem aviso', async () => {
    const wrapper = await montarHome(1, { logado: true })
    const del = vi.spyOn(apiClient, 'delete')

    await clicarEmSair(wrapper)

    expect(del).toHaveBeenCalledWith('/sessao/')
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(router.currentRoute.value.name).toBe('inicio')
    expect(wrapper.find('[data-teste="sair-aviso"]').exists()).toBe(false)
    await wrapper.get('.avatar').trigger('click')
    expect(wrapper.text()).toContain('Entrar na conta')
  })

  it('o servidor não confirma: avisa na Início, com role="alert"', async () => {
    const wrapper = await montarHome(1, { logado: true })
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await clicarEmSair(wrapper)

    const aviso = wrapper.get('[data-teste="sair-aviso"]')
    expect(aviso.attributes('role')).toBe('alert')
    expect(aviso.text()).toContain('o servidor não confirmou')
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(router.currentRoute.value.name).toBe('inicio')
  })
})
