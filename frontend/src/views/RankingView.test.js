import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

/**
 * RankingView (FE-13, RF27.2, RI12): ranking do semestre por campus, público,
 * com a lista (posição, apelido e patente, sem pontos), o vazio e a troca de
 * campus pelo SeletorCampus. Integração com a gamificacaoStore e o servidor
 * simulado.
 */
const AGORA = new Date(2026, 10, 23, 12, 0)

let pinia
async function montarEm(caminho, { campusLembrado = null } = {}) {
  if (campusLembrado) {
    localStorage.setItem('bandejao:preferencias', JSON.stringify({ campusId: campusLembrado }))
  }
  pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const linhas = (wrapper) => wrapper.findAll('[data-teste="linha-ranking"]')
const vazio = (wrapper) => wrapper.find('[data-teste="ranking-vazio"]')

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

describe('RankingView — lista (RF27.2)', () => {
  it('visitante vê o ranking do campus, sem login', async () => {
    const { wrapper } = await montarEm('/ranking/1')

    expect(wrapper.find('h1').text()).toBe('Ranking do semestre')
    expect(linhas(wrapper).length).toBeGreaterThan(0)
    expect(wrapper.text()).not.toContain('Entrar para')
  })

  it('até 10 linhas, cada uma com posição, apelido e patente (pelo nome)', async () => {
    const { wrapper } = await montarEm('/ranking/1')
    const { linhas: doServidor } = await apiClient.get('/ranking/1/')

    expect(linhas(wrapper)).toHaveLength(doServidor.length)
    expect(linhas(wrapper).length).toBeLessThanOrEqual(10)
    const primeira = linhas(wrapper)[0]
    expect(primeira.get('[data-teste="linha-posicao"]').text()).toBe('1º')
    expect(primeira.get('[data-teste="linha-apelido"]').text()).toBe(doServidor[0].apelido)
    // A patente aparece pelo nome do Anexo A, não pelo valor da API.
    expect(primeira.get('[data-teste="linha-patente"]').text()).not.toMatch(/_/)
  })

  it('nunca mostra pontos (RI12)', async () => {
    const { wrapper } = await montarEm('/ranking/1')

    expect(wrapper.get('[data-teste="ranking-lista"]').text()).not.toMatch(/pontos|pts/i)
  })

  it('a lista é ordenada (ol) e diz o semestre', async () => {
    const { wrapper } = await montarEm('/ranking/1')

    expect(wrapper.get('[data-teste="ranking-lista"]').element.tagName).toBe('OL')
    expect(wrapper.text()).toMatch(/2026\.2/)
  })

  it('diz o nome do campus', async () => {
    const { wrapper } = await montarEm('/ranking/3')

    await vi.waitFor(() => expect(wrapper.get('.subtitulo').text()).toContain('Gama'))
  })
})

describe('RankingView — vazio (RF27.2)', () => {
  it('campus sem ninguém no ranking: "Ninguém no ranking ainda", sem lista', async () => {
    const { wrapper } = await montarEm('/ranking/4')

    expect(vazio(wrapper).text()).toContain('Ninguém no ranking ainda')
    expect(linhas(wrapper)).toHaveLength(0)
  })
})

describe('RankingView — troca de campus pelo SeletorCampus', () => {
  it('escolher outro campus leva a /ranking/:campusId e troca a lista', async () => {
    const { wrapper, router } = await montarEm('/ranking/1')
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-teste="seletor-campus-opcao"]')).toHaveLength(5),
    )

    const planaltina = wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .find((b) => b.text() === 'Planaltina')
    await planaltina.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/ranking/4')
    expect(vazio(wrapper).exists()).toBe(true)
  })

  it('trocar o campus do ranking não troca o campus lembrado do cardápio', async () => {
    const { wrapper } = await montarEm('/ranking/1', { campusLembrado: 3 })
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-teste="seletor-campus-opcao"]')).toHaveLength(5),
    )

    await wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .find((b) => b.text() === 'Planaltina')
      .trigger('click')
    await flushPromises()

    expect(usePreferenciasStore().campusId).toBe(3)
  })
})

describe('RankingView — rotas e falhas', () => {
  it('/ranking sem campus vai para o ranking do campus lembrado', async () => {
    const { router } = await montarEm('/ranking', { campusLembrado: 3 })

    expect(router.currentRoute.value.fullPath).toBe('/ranking/3')
  })

  it('/ranking sem campus lembrado: pede para escolher o campus', async () => {
    const { wrapper } = await montarEm('/ranking')

    expect(wrapper.text()).toContain('Escolha um campus para ver o ranking.')
    expect(linhas(wrapper)).toHaveLength(0)
  })

  it('o título da aba é "Ranking · Bandejão"', async () => {
    await montarEm('/ranking/1')

    expect(document.title).toBe('Ranking · Bandejão')
  })

  it('campus inexistente: "Campus não encontrado"', async () => {
    const { wrapper } = await montarEm('/ranking/999')

    expect(wrapper.get('[data-teste="ranking-estado"]').text()).toContain('Campus não encontrado')
  })

  it('backend ainda sem o ranking (501): avisa que ainda não está disponível', async () => {
    simulacao.definirRankingDisponivel(false)
    const { wrapper } = await montarEm('/ranking/1')

    expect(wrapper.get('[data-teste="ranking-estado"]').text()).toContain(
      'O ranking ainda não está disponível.',
    )
  })

  it('falha ao carregar: mensagem e "Tentar de novo", que recupera', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    let falhar = true
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      if (caminho === '/ranking/1/' && falhar) {
        return Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
      }
      return getOriginal(caminho, opcoes)
    })
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { wrapper } = await montarEm('/ranking/1')
    const estado = wrapper.get('[data-teste="ranking-estado"]')
    expect(estado.text()).toContain('Sem internet.')

    falhar = false
    await estado.get('[data-teste="ranking-tentar-de-novo"]').trigger('click')
    await flushPromises()

    expect(linhas(wrapper).length).toBeGreaterThan(0)
  })
})
