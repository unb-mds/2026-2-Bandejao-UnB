import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import routerDoApp, { routes, instalarGuardas } from './index'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { CONTA_DEMO } from '@/services/mock/banco'
import { apiClient } from '@/services/apiClient'
import { useAuthStore } from '@/stores/auth'
import App from '@/App.vue'

// Segunda-feira, 28/09/2026, 12h.
const AGORA = new Date(2026, 8, 28, 12, 0)

async function montarEm(caminho, { campus = null } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (campus) usePreferenciasStore().escolherCampus(campus)

  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
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
  reiniciarSimulacao()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('roteamento', () => {
  it('na primeira visita a raiz mostra as boas-vindas', async () => {
    const { router, wrapper } = await montarEm('/')
    expect(router.currentRoute.value.name).toBe('boas-vindas')
    expect(wrapper.find('h1').text()).toBe('bandejão')
  })

  it('com campus lembrado, a raiz abre direto a tela do campus (RN04, RF05, RNF03)', async () => {
    const { router, wrapper } = await montarEm('/', { campus: 1 })
    expect(router.currentRoute.value.name).toBe('campus-tela')
    expect(router.currentRoute.value.params.campusId).toBe('1')
    await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Darcy Ribeiro'))
  })

  it('telas que dependem de campus pedem a escolha do campus antes', async () => {
    const { router } = await montarEm('/inicio')
    expect(router.currentRoute.value.name).toBe('campus')
  })

  it('/campus/:campusId abre a tela do campus e ele passa a ser o lembrado', async () => {
    const { wrapper } = await montarEm('/campus/3')
    await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Gama'))
    expect(JSON.parse(localStorage.getItem('bandejao:preferencias')).campusId).toBe(3)
  })

  it.each([['/campus/99'], ['/campus/darcy']])(
    '%s: "Campus não encontrado", sem virar o campus lembrado',
    async (caminho) => {
      const { wrapper } = await montarEm(caminho)
      await vi.waitFor(() => expect(wrapper.text()).toContain('Campus não encontrado'))
      expect(usePreferenciasStore().campusId).toBeNull()
    },
  )

  it.each([
    ['/cardapio', { name: 'campus-tela', params: { campusId: '1' } }],
    ['/fila', { name: 'campus-tela', params: { campusId: '1' }, hash: '#fila' }],
    ['/cardapio/3', { name: 'campus-tela', params: { campusId: '3' } }],
    ['/cardapio/darcy', { name: 'campus-tela', params: { campusId: '1' } }],
  ])('com campus lembrado, %s redireciona para a tela do campus', async (caminho, destino) => {
    const { router } = await montarEm(caminho, { campus: 1 })
    expect(router.currentRoute.value).toMatchObject(destino)
  })

  it.each([['/cardapio'], ['/fila'], ['/cardapio/darcy']])(
    'sem campus lembrado, %s leva à escolha do campus',
    async (caminho) => {
      const aviso = vi.spyOn(console, 'warn')
      const { router } = await montarEm(caminho)
      expect(router.currentRoute.value.name).toBe('campus')
      expect(aviso).not.toHaveBeenCalled()
    },
  )

  it.each([
    ['/login', 'Entrar'],
    ['/cadastro', 'Criar conta'],
    ['/confirmar-email', 'Confirmar e-mail'],
    ['/recuperar-senha', 'Recuperar senha'],
    ['/redefinir-senha', 'Redefinir senha'],
    ['/avaliacoes', 'Avaliações'],
  ])('%s renderiza a tela "%s"', async (caminho, titulo) => {
    const { wrapper } = await montarEm(caminho, { campus: 1 })
    expect(wrapper.find('h1').text()).toBe(titulo)
  })

  it('rota inexistente cai no 404', async () => {
    const { wrapper } = await montarEm('/qualquer-coisa')
    expect(wrapper.find('h1').text()).toBe('Página não encontrada')
  })
})

describe('navegação do protótipo', () => {
  it('visitante chega ao cardápio em 2 toques: continuar → campus (RNF03)', async () => {
    const { wrapper, router } = await montarEm('/')

    await wrapper
      .findAll('a')
      .find((a) => a.text() === 'Continuar sem login')
      .trigger('click')
    await esperarRota(router, 'campus')

    const botaoDarcy = () =>
      wrapper.findAll('button').find((b) => b.text().includes('Darcy Ribeiro'))
    await vi.waitFor(() => expect(botaoDarcy()).toBeTruthy())
    await botaoDarcy().trigger('click')
    await esperarRota(router, 'campus-tela')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(wrapper.text()).toContain('Frango grelhado ao molho de ervas')
  })

  it('visitante vê convite ao login em vez do formulário de avaliação (RF05)', async () => {
    const { wrapper } = await montarEm('/avaliacoes', { campus: 1 })
    expect(wrapper.text()).toContain('Avaliação bloqueada')
    expect(wrapper.find('textarea').exists()).toBe(false)
    // Os comentários continuam públicos.
    expect(wrapper.text()).toContain('lucas_unb')
  })
})

describe('cardápio', () => {
  it('pratos com marcador aparecem com o alerta "Contém" quando não há filtro (RF08)', async () => {
    const { wrapper } = await montarEm('/cardapio', { campus: 1 })
    const bife = wrapper.findAll('.prato').find((p) => p.text().includes('Bife acebolado'))
    expect(bife.text()).toContain('Contém:')
    expect(bife.text()).toContain('Suíno')
  })

  it('com o marcador selecionado, os pratos que o contêm são ocultados (RF08)', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 1, dieta: 'todos', marcadores: ['leite'] }),
    )
    const { wrapper } = await montarEm('/cardapio')
    expect(wrapper.text()).not.toContain('Purê de batata')
    expect(wrapper.text()).toContain('Sem opção compatível com o filtro ativo')
  })

  it('filtro de dieta oculta a linha padrão e "mostrar todas" reverte (RF09)', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 1, dieta: 'ovolacto', marcadores: [] }),
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
    const { wrapper } = await montarEm('/cardapio', { campus: 5 })
    expect(wrapper.text()).toContain('Cardápio ainda não publicado')
  })

  it('o filtro aplicado fica lembrado no aparelho', async () => {
    const { wrapper } = await montarEm('/cardapio', { campus: 1 })
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

describe('sessão ao abrir o app (FE-03, ADR 0007)', () => {
  it('o router do app já pergunta pela sessão na primeira navegação', async () => {
    setActivePinia(createPinia())
    const espiao = vi.spyOn(apiClient, 'get')

    await routerDoApp.push('/campus')

    expect(espiao).toHaveBeenCalledWith('/sessao/', { avisarSessaoPerdida: false })
    expect(useAuthStore().sessaoCarregada).toBe(true)
  })

  it('depois de recarregar a página, quem tem sessão continua logado', async () => {
    setActivePinia(createPinia())
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    // montarEm cria stores novas (como um F5); só o cookie de sessão continua.
    const { wrapper } = await montarEm('/inicio', { campus: 1 })

    expect(wrapper.find(`[aria-label="Perfil de ${CONTA_DEMO.apelido}"]`).exists()).toBe(true)
  })

  it('sem sessão, o app abre como visitante', async () => {
    const { wrapper } = await montarEm('/inicio', { campus: 1 })
    expect(wrapper.find('[aria-label="Perfil de Visitante"]').exists()).toBe(true)
  })

  it('busca a sessão uma vez só, não a cada navegação', async () => {
    const espiao = vi.spyOn(apiClient, 'get')
    const { router } = await montarEm('/login')

    await router.push('/cadastro')
    await router.push('/recuperar-senha')

    const pedidosDeSessao = espiao.mock.calls.filter(([caminho]) => caminho === '/sessao/')
    expect(pedidosDeSessao).toHaveLength(1)
  })
})
