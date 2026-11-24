import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { reiniciarAvisoLocalizacaoParaTestes } from '@/composables/avisoLocalizacao'
import { ApiError, apiClient } from '@/services/apiClient'
import { usePreferenciasStore } from '@/stores/preferencias'
import App from '@/App.vue'

/**
 * Boas-vindas (#285): o campus é escolhido nela mesma, sem o passo
 * "Continuar sem login". Sem permitir a localização, a primeira visita leva
 * 2 interações até o cardápio ("Agora não" e o campus), como no RNF03 da
 * Release 2.
 */

// Segunda-feira, 28/09/2026, 12h.
const AGORA = new Date(2026, 8, 28, 12, 0)

let wrapper
let router

function simularNavegador(estado = 'prompt') {
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn(async () => ({ state: estado })) },
    geolocation: { getCurrentPosition: vi.fn() },
  })
}

async function abrirPrimeiraVisita() {
  const pinia = createPinia()
  setActivePinia(pinia)
  router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push('/')
  await router.isReady()
  wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
}

const botaoDoCampus = (nome) =>
  wrapper.findAll('.boas-vindas button').find((botao) => botao.text().includes(nome))

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

describe('BoasVindasView: escolha do campus na própria boas-vindas (#285)', () => {
  it('sem permitir a localização, 2 interações até o cardápio: "Agora não" e o campus (RNF03)', async () => {
    simularNavegador()
    await abrirPrimeiraVisita()
    expect(router.currentRoute.value.name).toBe('boas-vindas')
    let interacoes = 0

    const aviso = wrapper.get('dialog.aviso-localizacao')
    await vi.waitFor(() => expect(aviso.attributes('open')).toBeDefined())
    const agoraNao = aviso.findAll('button').find((botao) => botao.text() === 'Agora não')
    await agoraNao.trigger('click')
    interacoes += 1
    await flushPromises()

    await vi.waitFor(() => expect(botaoDoCampus('Darcy Ribeiro')).toBeTruthy())
    await botaoDoCampus('Darcy Ribeiro').trigger('click')
    interacoes += 1

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('campus-tela'))
    expect(router.currentRoute.value.params.campusId).toBe('1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(interacoes).toBe(2)
  })

  it('a escolha fica lembrada no aparelho (RN04): a visita seguinte abre o campus direto', async () => {
    await abrirPrimeiraVisita()
    await vi.waitFor(() => expect(botaoDoCampus('Gama')).toBeTruthy())

    await botaoDoCampus('Gama').trigger('click')

    expect(usePreferenciasStore().campusId).toBe(3)
    await vi.waitFor(() => expect(router.currentRoute.value.params.campusId).toBe('3'))
  })

  it('continua com "Entrar na conta", e não tem mais o passo "Continuar sem login"', async () => {
    await abrirPrimeiraVisita()
    const tela = wrapper.get('.boas-vindas')

    const entrar = tela.findAll('a').find((link) => link.text() === 'Entrar na conta')
    expect(entrar.attributes('href')).toBe('/login')
    expect(tela.text()).not.toContain('Continuar sem login')
  })

  it('mostra todos os campi como botões, com um rótulo que diz para que servem', async () => {
    await abrirPrimeiraVisita()
    await vi.waitFor(() => expect(botaoDoCampus('Darcy Ribeiro')).toBeTruthy())

    const grupo = wrapper.get('.boas-vindas [role="group"]')
    expect(grupo.attributes('aria-labelledby')).toBeTruthy()
    const rotulo = wrapper.get(`#${grupo.attributes('aria-labelledby')}`)
    expect(rotulo.text()).toMatch(/campus/i)
    for (const nome of ['Darcy Ribeiro', 'Ceilândia', 'Gama', 'Planaltina']) {
      expect(botaoDoCampus(nome)).toBeTruthy()
    }
  })

  it('falha ao carregar os campi: avisa e deixa tentar de novo', async () => {
    // Só o primeiro GET /campi/ falha; a sessão e o resto seguem o simulado.
    const getOriginal = apiClient.get.bind(apiClient)
    let pedidosDosCampi = 0
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      if (caminho.startsWith('/campi/') && ++pedidosDosCampi === 1) {
        return Promise.reject(new ApiError(0, { codigo: null, mensagem: 'Sem conexão.' }))
      }
      return getOriginal(caminho, opcoes)
    })
    await abrirPrimeiraVisita()

    await vi.waitFor(() =>
      expect(wrapper.get('.boas-vindas').text()).toContain('Não foi possível carregar os campi.'),
    )
    const tentar = wrapper
      .findAll('.boas-vindas button')
      .find((botao) => botao.text() === 'Tentar novamente')
    await tentar.trigger('click')

    await vi.waitFor(() => expect(botaoDoCampus('Darcy Ribeiro')).toBeTruthy())
    expect(pedidosDosCampi).toBe(2)
  })
})
