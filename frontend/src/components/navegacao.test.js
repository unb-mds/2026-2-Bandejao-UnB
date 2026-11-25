import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { ITENS_NAVEGACAO, ITENS_NAVEGACAO_TOPO, itemAtivo } from '@/constants/navegacao'
import App from '@/App.vue'
import NavegacaoInferior from './NavegacaoInferior.vue'
import NavegacaoTopo from './NavegacaoTopo.vue'

async function montar(componente, caminho = '/cardapio') {
  const pinia = createPinia()
  setActivePinia(pinia)
  usePreferenciasStore().escolherCampus(1)
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

enableAutoUnmount(afterEach)

afterEach(() => {
  document.body.innerHTML = ''
})

const item = (rotulo) => ITENS_NAVEGACAO.find((i) => i.rotulo === rotulo)

describe('itemAtivo', () => {
  it.each([
    ['Cardápio', 'cardapio', true],
    ['Cardápio', 'campus-tela', true],
    ['Fila', 'campus-tela', false],
    ['Cardápio', 'cardapio-campus', true],
    ['Fila', 'fila', true],
    ['Fila', 'filas-historico', false],
    ['Avaliações', 'avaliacoes', true],
    ['Cardápio', 'fila', false],
    ['Cardápio', undefined, false],
    ['Cardápio', null, false],
    ['Início', 'inicio', false],
    ['Perfil', 'inicio', false],
  ])('%s na rota %s: %s', (rotulo, rota, esperado) => {
    expect(itemAtivo(item(rotulo), rota)).toBe(esperado)
  })

  it('com marcarInicio (barra do topo), só a Início acende na /inicio', () => {
    expect(itemAtivo(item('Início'), 'inicio', { marcarInicio: true })).toBe(true)
    expect(itemAtivo(item('Início'), 'fila', { marcarInicio: true })).toBe(false)
    expect(itemAtivo(item('Perfil'), 'inicio', { marcarInicio: true })).toBe(false)
  })
})

describe('NavegacaoTopo e NavegacaoInferior', () => {
  it('as duas levam aos mesmos destinos, na mesma ordem (o topo não repete o Perfil)', async () => {
    const { wrapper: topo } = await montar(NavegacaoTopo)
    const { wrapper: inferior } = await montar(NavegacaoInferior)

    const semPerfil = destinos(inferior).filter((d) => d.rotulo !== 'Perfil')
    expect(destinos(topo)).toEqual(semPerfil)
    expect(destinos(topo).map((d) => d.rotulo)).toEqual(ITENS_NAVEGACAO_TOPO.map((i) => i.rotulo))
    expect(new Set(destinos(topo).map((d) => d.href)).size).toBe(destinos(topo).length)
  })

  it('na /inicio, a do topo marca "Início" como página atual', async () => {
    const { wrapper } = await montar(NavegacaoTopo, '/inicio')

    const atuais = wrapper.findAll('[aria-current="page"]')

    expect(atuais).toHaveLength(1)
    expect(atuais[0].text()).toBe('Início')
  })

  it('a do topo tem o canal de contato (RNF08): o e-mail da equipe', async () => {
    const { wrapper } = await montar(NavegacaoTopo)

    const contato = wrapper.findAll('a').find((a) => a.text().startsWith('Contato'))

    expect(contato.attributes('href')).toBe('mailto:equipe@bandejaounb.com.br')
    // O endereço chega a quem usa leitor de tela uma vez só: sem `title` repetindo.
    expect(contato.text()).toContain('equipe@bandejaounb.com.br')
    expect(contato.attributes('title')).toBeUndefined()
    expect(contato.attributes('target')).toBeUndefined()
  })

  it.each([
    ['NavegacaoTopo', NavegacaoTopo],
    ['NavegacaoInferior', NavegacaoInferior],
  ])('%s marca a página atual com aria-current', async (_nome, componente) => {
    const { wrapper } = await montar(componente, '/avaliacoes')

    const atuais = wrapper.findAll('[aria-current="page"]')

    expect(atuais).toHaveLength(1)
    expect(atuais[0].text()).toBe('Avaliações')
  })

  it.each([
    ['NavegacaoTopo', NavegacaoTopo],
    ['NavegacaoInferior', NavegacaoInferior],
  ])('%s marca "Cardápio" na tela do campus', async (_nome, componente) => {
    const { wrapper } = await montar(componente, '/campus/1')

    const atuais = wrapper.findAll('[aria-current="page"]')

    expect(atuais).toHaveLength(1)
    expect(atuais[0].text()).toBe('Cardápio')
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

  it('aparece quando a primeira rota é resolvida', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    usePreferenciasStore().escolherCampus(1)
    const router = createRouter({ history: createMemoryHistory(), routes })
    const wrapper = mount(App, { global: { plugins: [pinia, router] } })
    expect(wrapper.findComponent(NavegacaoTopo).exists()).toBe(false)

    await router.push('/fila')
    await flushPromises()

    expect(wrapper.findComponent(NavegacaoTopo).exists()).toBe(true)
  })

  it('com a barra do topo, a tela continua com um só landmark "banner"', async () => {
    const { wrapper } = await montar(App, '/fila')

    expect(wrapper.findComponent(NavegacaoTopo).exists()).toBe(true)
    expect(wrapper.findAll('header')).toHaveLength(1)
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

describe('Tela "Fila do RU" (/fila)', () => {
  it('as três navegações marcam "Fila", não "Cardápio"', async () => {
    const { wrapper } = await montar(App, '/fila')

    const atuais = wrapper
      .findAll('nav a[aria-current="page"]')
      .map((link) => link.text().replace(/\s+/g, ' ').trim())
    expect(atuais.length).toBeGreaterThan(0)
    expect(atuais.every((texto) => texto.startsWith('Fila'))).toBe(true)
  })
})
