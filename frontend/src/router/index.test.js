import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { routes, exigirCampus } from './index'
import { usePreferenciasStore } from '@/stores/preferencias'
import { banco } from '@/services/mock/servidor'
import App from '@/App.vue'

// Segunda-feira, 28/09/2026, 12h.
const AGORA = new Date(2026, 8, 28, 12, 0)

async function montarEm(caminho, { campus = null } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (campus) usePreferenciasStore().escolherCampus(campus)

  const router = createRouter({ history: createMemoryHistory(), routes })
  router.beforeEach(exigirCampus)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

/** As views são lazy-loaded: espera a rota (e o componente) chegarem. */
async function esperarRota(router, nome) {
  await vi.waitFor(() => expect(router.currentRoute.value.name).toBe(nome))
  await flushPromises()
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(AGORA)
  localStorage.clear()
  banco.reiniciar()
})

afterEach(() => {
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('roteamento', () => {
  it('na primeira visita a raiz mostra as boas-vindas', async () => {
    const { router, wrapper } = await montarEm('/')
    expect(router.currentRoute.value.name).toBe('boas-vindas')
    expect(wrapper.find('h1').text()).toBe('bandejão')
  })

  it('com campus lembrado, a raiz abre direto o cardápio (RF05, RNF03)', async () => {
    const { router, wrapper } = await montarEm('/', { campus: 'darcy' })
    expect(router.currentRoute.value.name).toBe('cardapio')
    expect(wrapper.find('h1').text()).toBe('Cardápio')
  })

  it('telas que dependem de campus pedem a escolha do campus antes', async () => {
    const { router } = await montarEm('/inicio')
    expect(router.currentRoute.value.name).toBe('campus')
  })

  it('/cardapio/:campusId passa a ser o campus lembrado', async () => {
    const { wrapper } = await montarEm('/cardapio/gama')
    expect(wrapper.text()).toContain('Gama (FGA)')
    expect(JSON.parse(localStorage.getItem('bandejao:preferencias')).campusId).toBe('gama')
  })

  it('campus inexistente cai no 404', async () => {
    const { wrapper } = await montarEm('/cardapio/executivo')
    expect(wrapper.find('h1').text()).toBe('Página não encontrada')
  })

  it.each([
    ['/login', 'Entrar'],
    ['/cadastro', 'Criar conta'],
    ['/confirmar-email', 'Confirmar e-mail'],
    ['/recuperar-senha', 'Recuperar senha'],
    ['/redefinir-senha', 'Redefinir senha'],
    ['/avaliacoes', 'Avaliações'],
    ['/fila', 'Fila do RU'],
  ])('%s renderiza a tela "%s"', async (caminho, titulo) => {
    const { wrapper } = await montarEm(caminho, { campus: 'darcy' })
    expect(wrapper.find('h1').text()).toBe(titulo)
  })

  it('rota inexistente cai no 404', async () => {
    const { wrapper } = await montarEm('/qualquer-coisa')
    expect(wrapper.find('h1').text()).toBe('Página não encontrada')
  })
})

describe('navegação do protótipo', () => {
  it('visitante chega ao cardápio em 3 toques: continuar → campus → cardápio (RNF03)', async () => {
    const { wrapper, router } = await montarEm('/')

    await wrapper
      .findAll('a')
      .find((a) => a.text() === 'Continuar sem login')
      .trigger('click')
    await esperarRota(router, 'campus')

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Darcy Ribeiro'))
      .trigger('click')
    await esperarRota(router, 'inicio')

    await vi.waitFor(() => expect(wrapper.find('.cartao-hoje').exists()).toBe(true))
    await wrapper.find('.cartao-hoje').trigger('click')
    await esperarRota(router, 'cardapio')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(wrapper.text()).toContain('Frango grelhado ao molho de ervas')
  })

  it('visitante vê convite ao login em vez do formulário de avaliação (RF05)', async () => {
    const { wrapper } = await montarEm('/avaliacoes', { campus: 'darcy' })
    expect(wrapper.text()).toContain('Avaliação bloqueada')
    expect(wrapper.find('textarea').exists()).toBe(false)
    // Os comentários continuam públicos.
    expect(wrapper.text()).toContain('lucas_unb')
  })
})

describe('cardápio', () => {
  it('pratos com marcador aparecem com o alerta "Contém" quando não há filtro (RF08)', async () => {
    const { wrapper } = await montarEm('/cardapio', { campus: 'darcy' })
    const bife = wrapper.findAll('.prato').find((p) => p.text().includes('Bife acebolado'))
    expect(bife.text()).toContain('Contém:')
    expect(bife.text()).toContain('Suíno')
  })

  it('com o marcador selecionado, os pratos que o contêm são ocultados (RF08)', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 'darcy', dieta: 'todos', marcadores: ['leite'] }),
    )
    const { wrapper } = await montarEm('/cardapio')
    expect(wrapper.text()).not.toContain('Purê de batata')
    expect(wrapper.text()).toContain('Sem opção compatível com o filtro ativo')
  })

  it('filtro de dieta oculta a linha padrão e "mostrar todas" reverte (RF09)', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 'darcy', dieta: 'ovolacto', marcadores: [] }),
    )
    const { wrapper } = await montarEm('/cardapio')
    expect(wrapper.text()).not.toContain('Bife acebolado')
    expect(wrapper.text()).toContain('Omelete de legumes')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Mostrar todas')
      .trigger('click')
    expect(wrapper.text()).toContain('Bife acebolado')
  })

  it('campus sem cardápio publicado mostra o aviso (RF07)', async () => {
    const { wrapper } = await montarEm('/cardapio', { campus: 'fal' })
    expect(wrapper.text()).toContain('Cardápio ainda não publicado')
  })

  it('o filtro aplicado fica lembrado no aparelho', async () => {
    const { wrapper } = await montarEm('/cardapio', { campus: 'darcy' })
    await wrapper.find('button[aria-label="Filtros alimentares"]').trigger('click')
    await wrapper
      .findAll('.opcao-marcador')
      .find((b) => b.text() === 'Suíno')
      .trigger('click')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Aplicar')
      .trigger('click')
    await flushPromises()

    expect(wrapper.text()).not.toContain('Bife acebolado')
    expect(JSON.parse(localStorage.getItem('bandejao:preferencias')).marcadores).toEqual(['suino'])
  })
})
