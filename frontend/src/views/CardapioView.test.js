import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'
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

async function montarComRouter(caminho) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  await vi.waitFor(() => expect(wrapper.find('.prato, .estado-titulo').exists()).toBe(true))
  return { wrapper, router }
}

function adiada() {
  let resolver
  const promessa = new Promise((ok) => {
    resolver = ok
  })
  return { promessa, resolver }
}

const abasDaSemana = (wrapper) =>
  wrapper.findAll('[role="tablist"][aria-label="Dia da semana"] [role="tab"]')

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

describe('CardapioView: seleção, troca de campus e respostas fora de ordem (FE-08)', () => {
  it('resposta atrasada de outro dia não tira a aba escolhida por último', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    const atrasos = {}
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      const dia = new URL(caminho, 'http://x').searchParams.get('dia')
      if (caminho.startsWith('/cardapio/?') && ['2026-09-29', '2026-09-30'].includes(dia)) {
        atrasos[dia] = adiada()
        return atrasos[dia].promessa.then(() => getOriginal(caminho, opcoes))
      }
      return getOriginal(caminho, opcoes)
    })
    const wrapper = await montarEm('/campus/1')
    const abas = abasDaSemana(wrapper)

    await abas[1].trigger('click')
    await abas[2].trigger('click')
    atrasos['2026-09-30'].resolver()
    await flushPromises()
    atrasos['2026-09-29'].resolver()
    await flushPromises()

    expect(abas[2].attributes('aria-selected')).toBe('true')
    expect(abas[1].attributes('aria-selected')).toBe('false')
    expect(usePreferenciasStore().dataSelecionada).toBe('2026-09-30')
  })

  it('trocar de campus limpa dia e refeição e faz um pedido só para o novo campus', async () => {
    const get = vi.spyOn(apiClient, 'get')
    const { wrapper, router } = await montarComRouter('/campus/1')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-jantar"]').exists()).toBe(true),
    )
    await wrapper.get('[data-teste="refeicao-jantar"]').trigger('click')
    await flushPromises()
    const antes = pedidosDoCardapio(get).length

    await router.push('/campus/3')
    await flushPromises()

    const novos = pedidosDoCardapio(get).slice(antes)
    expect(novos).toEqual([{ campus: '3' }])
  })

  it('dia escolhido numa semana que já passou é descartado ao abrir a seção', async () => {
    usePreferenciasStore().selecionar('2026-09-21', 'jantar')
    const get = vi.spyOn(apiClient, 'get')

    await montarEm('/campus/1')

    expect(pedidosDoCardapio(get)[0]).toEqual({ campus: '1' })
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

  it('sábado sem serviço e sem próximo dia na semana: "Sem refeições neste dia" (resposta do simulado)', async () => {
    const wrapper = await montarEm('/campus/3')

    const abas = abasDaSemana(wrapper)
    await abas[5].trigger('click')
    await flushPromises()

    await vi.waitFor(() => expect(wrapper.text()).toContain('Sem refeições neste dia'))
    expect(wrapper.text()).not.toContain('Cardápio ainda não publicado')
    expect(abas[5].attributes('aria-selected')).toBe('true')
  })

  it('refeição que o dia não serve: avisa, sem mandar ajustar filtros', async () => {
    simulacao.definirResumoDoDiaDisponivel(false)
    const wrapper = await montarEm('/campus/4')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-jantar"]').exists()).toBe(true),
    )

    await wrapper.get('[data-teste="refeicao-jantar"]').trigger('click')
    await flushPromises()

    await vi.waitFor(() =>
      expect(wrapper.text()).toContain('Esta refeição não é servida neste dia.'),
    )
    expect(wrapper.get('[data-teste="refeicao-jantar"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.text()).not.toContain('Tente ajustar os filtros')
  })

  it('backend que responde com o próximo dia: avisa e mantém a aba escolhida', async () => {
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

  it('nenhuma categoria depois do filtro de dieta: "Nenhuma opção encontrada"', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 1, dieta: 'vegetariano_estrito', marcadores: [] }),
    )
    setActivePinia((pinia = createPinia()))
    responderCardapio({ categorias: [] })

    const wrapper = await montarEm('/campus/1')

    expect(wrapper.text()).toContain('Nenhuma opção encontrada')
    expect(wrapper.text()).toContain('Tente ajustar os filtros')
  })

  it('400 com filtros salvos: oferece "Limpar filtros" em vez de "Tentar novamente"', async () => {
    localStorage.setItem(
      'bandejao:preferencias',
      JSON.stringify({ campusId: 1, dieta: 'sem_filtro', marcadores: ['soja'] }),
    )
    setActivePinia((pinia = createPinia()))
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      const url = new URL(caminho, 'http://x')
      if (url.pathname === '/cardapio/' && url.searchParams.has('marcadores')) {
        return Promise.reject(
          new ApiError(400, {
            codigo: 'parametros_invalidos',
            mensagem: 'Marcador desconhecido: soja.',
          }),
        )
      }
      return getOriginal(caminho, opcoes)
    })

    const wrapper = await montarEm('/campus/1')

    expect(wrapper.text()).toContain('Marcador desconhecido: soja.')
    expect(wrapper.text()).not.toContain('Tentar novamente')
    await wrapper.get('[data-teste="limpar-filtros"]').trigger('click')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(usePreferenciasStore().marcadores).toEqual([])
  })

  it('"Tentar novamente" depois de uma falha pede de novo e mostra o cardápio', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    let falhar = true
    const get = vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      if (caminho.startsWith('/cardapio/?') && falhar) {
        falhar = false
        return Promise.reject(
          new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
        )
      }
      return getOriginal(caminho, opcoes)
    })

    const wrapper = await montarEm('/campus/1')
    expect(wrapper.text()).toContain('Fora do ar.')

    await wrapper
      .findAll('button')
      .find((botao) => botao.text() === 'Tentar novamente')
      .trigger('click')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(pedidosDoCardapio(get)).toHaveLength(2)
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
