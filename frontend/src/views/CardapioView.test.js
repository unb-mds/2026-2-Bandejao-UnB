import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)

let pinia
async function montarEm(caminho) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  await vi.waitFor(() => expect(wrapper.find('.prato, .estado-titulo').exists()).toBe(true))
  return wrapper
}

const pedidosDoCardapio = (get) =>
  get.mock.calls
    .map(([caminho]) => new URL(caminho, 'http://x'))
    .filter((url) => url.pathname === '/cardapio/')
    .map((url) => Object.fromEntries(url.searchParams))

function responderCardapio(resposta) {
  const getOriginal = apiClient.get.bind(apiClient)
  return vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
    caminho.startsWith('/cardapio/?')
      ? Promise.resolve({
          campus: 1,
          status: 'publicado',
          data: '2026-09-28',
          refeicao: 'almoco',
          refeicaoEncerrada: false,
          alergenosIndisponivel: false,
          filtroMarcadorDesativado: false,
          avisoSujeitoAAlteracao: 'Sujeito a alteração.',
          categorias: [],
          ...resposta,
        })
      : getOriginal(caminho, opcoes),
  )
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  localStorage.clear()
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('CardapioView ligada ao GET /api/cardapio/ (FE-08)', () => {
  it('abre a refeição padrão (RN05) e o seletor mostra a nota de cada refeição', async () => {
    const wrapper = await montarEm('/campus/1')

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-cafe"]').exists()).toBe(true),
    )
    expect(wrapper.get('[data-teste="refeicao-almoco"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('[data-teste="refeicao-cafe"]').text()).toMatch(/★ \d,\d/)
    expect(wrapper.get('[data-teste="refeicao-jantar"]').text()).toContain('Sem nota')
  })

  it('AbasSemana: de segunda a sábado; trocar de dia pede o cardápio daquele dia', async () => {
    const get = vi.spyOn(apiClient, 'get')
    const wrapper = await montarEm('/campus/1')

    const abas = wrapper.findAll('[role="tablist"][aria-label="Dia da semana"] [role="tab"]')
    expect(abas).toHaveLength(6)
    await abas[1].trigger('click')
    await flushPromises()

    expect(pedidosDoCardapio(get).at(-1)).toMatchObject({ campus: '1', dia: '2026-09-29' })
    expect(abas[1].attributes('aria-selected')).toBe('true')
  })

  it('trocar de refeição pede o cardápio dela', async () => {
    const get = vi.spyOn(apiClient, 'get')
    const wrapper = await montarEm('/campus/1')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-jantar"]').exists()).toBe(true),
    )

    await wrapper.get('[data-teste="refeicao-jantar"]').trigger('click')
    await flushPromises()

    expect(pedidosDoCardapio(get).at(-1)).toMatchObject({ refeicao: 'jantar' })
  })

  it('os filtros lembrados vão como parâmetros, e o filtro no cliente saiu', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 1, dieta: 'vegetariano_estrito', marcadores: ['soja'] }),
    )
    setActivePinia((pinia = createPinia()))
    const get = vi.spyOn(apiClient, 'get')

    const wrapper = await montarEm('/campus/1')

    expect(pedidosDoCardapio(get)[0]).toMatchObject({
      campus: '1',
      dieta: 'vegetariano_estrito',
      marcadores: 'soja',
    })
    expect(wrapper.text()).toContain('Tofu grelhado ao shoyu')
  })

  it('aplicar um filtro pede o cardápio de novo com ele', async () => {
    const get = vi.spyOn(apiClient, 'get')
    await montarEm('/campus/1')

    usePreferenciasStore().aplicarFiltros('ovolactovegetariano', ['ovo'])
    await flushPromises()

    expect(pedidosDoCardapio(get).at(-1)).toMatchObject({
      dieta: 'ovolactovegetariano',
      marcadores: 'ovo',
    })
  })
})

describe('CardapioView: dias e refeições da semana (RF07.1)', () => {
  it('sem o resumo do dia, o seletor ainda deixa escolher café, almoço e jantar', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho.startsWith('/avaliacoes/resumo/')
        ? Promise.reject(new ApiError(501, {}))
        : getOriginal(caminho, opcoes),
    )

    const wrapper = await montarEm('/campus/1')

    for (const tipo of ['cafe', 'almoco', 'jantar']) {
      expect(wrapper.find(`[data-teste="refeicao-${tipo}"]`).exists()).toBe(true)
    }
    expect(wrapper.get('[data-teste="refeicao-cafe"]').text()).toContain('Sem nota')
  })

  it('dia sem serviço: avisa e mantém a aba escolhida', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      const url = new URL(caminho, 'http://x')
      if (url.pathname === '/cardapio/' && url.searchParams.get('dia') === '2026-10-03') {
        return getOriginal('/cardapio/?campus=3&dia=2026-10-02', opcoes)
      }
      return getOriginal(caminho, opcoes)
    })
    const wrapper = await montarEm('/campus/3')

    const abas = wrapper.findAll('[role="tablist"][aria-label="Dia da semana"] [role="tab"]')
    await abas[5].trigger('click')
    await flushPromises()

    await vi.waitFor(() => expect(wrapper.text()).toContain('Sem refeições neste dia'))
    expect(abas[5].attributes('aria-selected')).toBe('true')
    expect(wrapper.find('.prato').exists()).toBe(false)
  })
})

describe('CardapioView: estados vazios e avisos (FE-08)', () => {
  it('cardápio não publicado', async () => {
    const wrapper = await montarEm('/campus/5')

    expect(wrapper.text()).toContain('Cardápio ainda não publicado')
  })

  it('nenhuma categoria depois dos filtros: "Nenhuma opção encontrada"', async () => {
    responderCardapio({ categorias: [] })

    const wrapper = await montarEm('/campus/1')

    expect(wrapper.text()).toContain('Nenhuma opção encontrada')
  })

  it('filtro de marcadores desativado: avisa o motivo e não mostra "Contém"', async () => {
    responderCardapio({
      alergenosIndisponivel: true,
      filtroMarcadorDesativado: true,
      categorias: [
        {
          nome: 'Guarnição',
          semOpcaoCompativel: false,
          pratos: [
            {
              descricao: 'Purê de batata',
              marcadores: ['leite_e_derivados'],
              contemMarcadorSelecionado: false,
            },
          ],
        },
      ],
    })

    const wrapper = await montarEm('/campus/1')

    expect(wrapper.find('[data-teste="filtro-desativado"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Purê de batata')
    expect(wrapper.text()).not.toContain('Contém:')
  })

  it('mostra o aviso de que o cardápio está sujeito a alteração', async () => {
    responderCardapio({
      categorias: [
        {
          nome: 'Salada',
          semOpcaoCompativel: false,
          pratos: [{ descricao: 'Alface', marcadores: [], contemMarcadorSelecionado: false }],
        },
      ],
    })

    const wrapper = await montarEm('/campus/1')

    expect(wrapper.text()).toContain('Sujeito a alteração.')
  })
})
