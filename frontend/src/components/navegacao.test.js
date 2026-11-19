import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { CANAL_CONTATO } from '@/constants/contato'
import { ITENS_NAVEGACAO } from '@/constants/navegacao'
import App from '@/App.vue'
import NavegacaoInferior from './NavegacaoInferior.vue'
import NavegacaoTopo from './NavegacaoTopo.vue'

async function montar(componente, caminho = '/cardapio') {
  const pinia = createPinia()
  setActivePinia(pinia)
  usePreferenciasStore().escolherCampus('darcy')
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(componente, {
    global: { plugins: [pinia, router] },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router }
}

const destinos = (wrapper) =>
  wrapper
    .find('nav')
    .findAll('a[href^="/"]')
    .map((link) => ({
      rotulo: link.text(),
      href: link.attributes('href'),
    }))

beforeEach(() => {
  localStorage.clear()
  reiniciarSimulacao()
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('NavegacaoTopo e NavegacaoInferior', () => {
  it('as duas levam aos mesmos destinos, na mesma ordem', async () => {
    const { wrapper: topo } = await montar(NavegacaoTopo)
    const { wrapper: inferior } = await montar(NavegacaoInferior)

    expect(destinos(topo)).toEqual(destinos(inferior))
    expect(destinos(topo).map((d) => d.rotulo)).toEqual(ITENS_NAVEGACAO.map((i) => i.rotulo))
  })

  it('a do topo tem o canal de contato (RNF08), abrindo em outra aba com segurança', async () => {
    const { wrapper } = await montar(NavegacaoTopo)

    const contato = wrapper.find(`a[href="${CANAL_CONTATO}"]`)

    expect(contato.exists()).toBe(true)
    expect(contato.attributes('target')).toBe('_blank')
    expect(contato.attributes('rel')).toContain('noopener')
  })

  it.each([
    ['NavegacaoTopo', NavegacaoTopo],
    ['NavegacaoInferior', NavegacaoInferior],
  ])('%s marca a página atual com aria-current', async (_nome, componente) => {
    const { wrapper } = await montar(componente, '/fila')

    const atuais = wrapper.findAll('[aria-current="page"]')

    expect(atuais).toHaveLength(1)
    expect(atuais[0].text()).toBe('Fila')
  })

  it.each([
    ['NavegacaoTopo', NavegacaoTopo],
    ['NavegacaoInferior', NavegacaoInferior],
  ])('%s só usa links de verdade (teclado e mouse, não só toque)', async (_nome, componente) => {
    const { wrapper } = await montar(componente)

    const itens = wrapper.find('nav').element.children

    expect(itens.length).toBeGreaterThan(0)
    for (const item of itens) {
      expect(item.tagName).toBe('A')
      expect(item.getAttribute('href')).toBeTruthy()
    }
  })

  it('cada navegação é um marco "nav" com nome acessível', async () => {
    const { wrapper: topo } = await montar(NavegacaoTopo)
    const { wrapper: inferior } = await montar(NavegacaoInferior)

    expect(topo.find('nav').attributes('aria-label')).toBe('Navegação principal')
    expect(inferior.find('nav').attributes('aria-label')).toBe('Navegação principal')
  })
})

describe('App: navegação do topo', () => {
  it('aparece nas telas do app', async () => {
    const { wrapper } = await montar(App, '/fila')
    expect(wrapper.findComponent(NavegacaoTopo).exists()).toBe(true)
  })

  it('não aparece antes de a primeira rota ser resolvida (sem piscar na primeira visita)', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createRouter({ history: createMemoryHistory(), routes })

    // Sem push: a rota ainda é a inicial, sem nome, como no instante em que o app monta.
    const wrapper = mount(App, { global: { plugins: [pinia, router] } })

    expect(wrapper.findComponent(NavegacaoTopo).exists()).toBe(false)
  })

  it('não usa <header>: cada tela fica com um só landmark "banner"', async () => {
    const { wrapper } = await montar(NavegacaoTopo)

    expect(wrapper.find('header').exists()).toBe(false)
    expect(wrapper.find('nav[aria-label="Navegação principal"]').exists()).toBe(true)
  })

  it('não aparece na boas-vindas (primeira visita, antes de escolher o campus)', async () => {
    localStorage.clear()
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createRouter({ history: createMemoryHistory(), routes })
    router.push('/boas-vindas')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [pinia, router] } })
    await flushPromises()

    expect(wrapper.findComponent(NavegacaoTopo).exists()).toBe(false)
  })
})
