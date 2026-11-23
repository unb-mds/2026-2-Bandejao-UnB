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

function adiada() {
  let resolver
  const promessa = new Promise((ok) => (resolver = ok))
  return { promessa, resolver }
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

  it('nunca mostra pontos (RI12), mesmo que a resposta traga o campo', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/ranking/1/'
        ? Promise.resolve({
            campusId: 1,
            semestre: '2026.2',
            linhas: [
              { posicao: 1, apelido: 'ana', patente: 'VETERANO', pontos: 480 },
              { posicao: 2, apelido: 'bia', patente: 'RATO_DE_RU', pontos: 175 },
            ],
          })
        : getOriginal(caminho, opcoes),
    )
    const { wrapper } = await montarEm('/ranking/1')

    expect(linhas(wrapper)).toHaveLength(2)
    expect(wrapper.text()).not.toContain('480')
    expect(wrapper.text()).not.toContain('175')
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
    const { wrapper } = await montarEm('/ranking/5')

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

    const fazenda = wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .find((b) => b.text() === 'Fazenda Água Limpa')
    await fazenda.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/ranking/5')
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
    simulacao.definirGamificacaoDisponivel(false)
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
    const log = vi.spyOn(console, 'error')
    const { wrapper } = await montarEm('/ranking/1')
    const estado = wrapper.get('[data-teste="ranking-estado"]')
    expect(estado.text()).toContain('Sem internet.')
    expect(log).not.toHaveBeenCalled()

    falhar = false
    await estado.get('[data-teste="ranking-tentar-de-novo"]').trigger('click')
    await flushPromises()

    expect(linhas(wrapper).length).toBeGreaterThan(0)
  })
})

/** Casos da revisão do PR #242. */
describe('RankingView — id de campus mal formado', () => {
  it.each(['abc', '0', '01', '-1', '1.5'])(
    '/ranking/%s: "Campus não encontrado" sem chamar a API do ranking',
    async (id) => {
      const get = vi.spyOn(apiClient, 'get')
      const { wrapper } = await montarEm(`/ranking/${id}`)

      expect(wrapper.get('[data-teste="ranking-estado"]').text()).toContain('Campus não encontrado')
      expect(get.mock.calls.filter(([caminho]) => caminho.startsWith('/ranking/'))).toEqual([])
    },
  )

  it('o cartão de "Campus não encontrado" é anunciado (role="status")', async () => {
    const { wrapper } = await montarEm('/ranking/999')

    expect(wrapper.get('[data-teste="ranking-estado"]').attributes('role')).toBe('status')
  })
})

describe('RankingView — 404 fora do contrato', () => {
  it('um 404 sem `campus_nao_encontrado` (proxy, URL errada) vira erro, não "Campus não encontrado"', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/ranking/1/'
        ? Promise.reject(new ApiError(404, {}))
        : getOriginal(caminho, opcoes),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { wrapper } = await montarEm('/ranking/1')

    const estado = wrapper.get('[data-teste="ranking-estado"]')
    expect(estado.text()).not.toContain('Campus não encontrado')
    expect(estado.find('[data-teste="ranking-tentar-de-novo"]').exists()).toBe(true)
  })
})

describe('RankingView — mensagens de erro', () => {
  it('resposta sem a lista: a mensagem não se repete', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/ranking/1/'
        ? Promise.resolve({ campusId: 1, semestre: '2026.2' })
        : getOriginal(caminho, opcoes),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { wrapper } = await montarEm('/ranking/1')

    const texto = wrapper.get('[data-teste="ranking-estado"]').text()
    expect(texto.match(/Não foi possível carregar o ranking/g)).toHaveLength(1)
  })
})

describe('RankingView — troca rápida de campus', () => {
  it('respostas fora de ordem: a tela fica com o último campus escolhido', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    const doDarcy = adiada()
    const daFazenda = adiada()
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      if (caminho === '/ranking/1/') return doDarcy.promessa.then(() => getOriginal(caminho))
      if (caminho === '/ranking/5/') return daFazenda.promessa.then(() => getOriginal(caminho))
      return getOriginal(caminho, opcoes)
    })
    const { wrapper, router } = await montarEm('/ranking/1')
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-teste="seletor-campus-opcao"]')).toHaveLength(5),
    )

    await wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .find((b) => b.text() === 'Fazenda Água Limpa')
      .trigger('click')
    daFazenda.resolver()
    await flushPromises()
    doDarcy.resolver()
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/ranking/5')
    expect(vazio(wrapper).exists()).toBe(true)
    expect(linhas(wrapper)).toHaveLength(0)
  })
})

describe('RankingView — falha com o ranking já na tela', () => {
  it('a lista continua, com um aviso e "Tentar de novo"', async () => {
    const { wrapper } = await montarEm('/ranking/1')
    const quantas = linhas(wrapper).length
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )
    const log = vi.spyOn(console, 'error')
    const { useGamificacaoStore } = await import('@/stores/gamificacao')

    await useGamificacaoStore().carregarRanking(1, { forcar: true })
    await flushPromises()

    expect(linhas(wrapper)).toHaveLength(quantas)
    const aviso = wrapper.get('[data-teste="ranking-aviso"]')
    expect(aviso.text()).toContain('Não foi possível atualizar o ranking.')
    expect(log).not.toHaveBeenCalled()

    // "Tentar de novo": o aviso some e a lista é a nova.
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/ranking/1/'
        ? Promise.resolve({
            campusId: 1,
            semestre: '2026.2',
            linhas: [{ posicao: 1, apelido: 'recem_chegada', patente: 'VETERANO' }],
          })
        : getOriginal(caminho, opcoes),
    )
    await aviso.get('[data-teste="ranking-tentar-de-novo"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-teste="ranking-aviso"]').exists()).toBe(false)
    expect(linhas(wrapper)).toHaveLength(1)
    expect(linhas(wrapper)[0].text()).toContain('recem_chegada')
  })
})

/** Casos da segunda revisão do PR #242. */
describe('RankingView — patente pelo nome', () => {
  it('RATO_DE_RU aparece como "Rato de RU", não pelo valor da API', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho === '/ranking/1/'
        ? Promise.resolve({
            campusId: 1,
            semestre: '2026.2',
            linhas: [{ posicao: 1, apelido: 'ana', patente: 'RATO_DE_RU' }],
          })
        : getOriginal(caminho, opcoes),
    )
    const { wrapper } = await montarEm('/ranking/1')

    expect(linhas(wrapper)[0].get('[data-teste="linha-patente"]').text()).toBe('Rato de RU')
  })
})

describe('RankingView — atualizando sem piscar', () => {
  it.each(['carregando', 'desatualizado'])(
    'com o ranking na tela e a situação "%s", a lista continua',
    async (situacao) => {
      const { wrapper } = await montarEm('/ranking/1')
      const quantas = linhas(wrapper).length
      const { useGamificacaoStore } = await import('@/stores/gamificacao')
      const gamificacao = useGamificacaoStore()
      // A busca nova nunca termina: o que importa é a tela enquanto isso.
      vi.spyOn(apiClient, 'get').mockImplementation(() => new Promise(() => {}))

      gamificacao.rankings[1] = { ...gamificacao.rankings[1], situacao }
      await flushPromises()

      expect(linhas(wrapper)).toHaveLength(quantas)
      expect(wrapper.text()).not.toContain('Carregando ranking…')
    },
  )
})

describe('RankingView — depois do logout ou de um 401 (limpar)', () => {
  it('a tela busca o ranking de novo, sem ficar presa em "Carregando ranking…"', async () => {
    const { wrapper } = await montarEm('/ranking/1')
    const { useGamificacaoStore } = await import('@/stores/gamificacao')
    const get = vi.spyOn(apiClient, 'get')

    useGamificacaoStore().limpar()
    await flushPromises()

    expect(get).toHaveBeenCalledWith('/ranking/1/')
    expect(linhas(wrapper).length).toBeGreaterThan(0)
    expect(wrapper.text()).not.toContain('Carregando ranking…')
  })

  it('invalidarRanking: a tela busca de novo, mantendo a lista enquanto isso', async () => {
    const { wrapper } = await montarEm('/ranking/1')
    const { useGamificacaoStore } = await import('@/stores/gamificacao')
    const get = vi.spyOn(apiClient, 'get')

    useGamificacaoStore().invalidarRanking(1)
    await flushPromises()

    expect(get).toHaveBeenCalledWith('/ranking/1/')
    expect(linhas(wrapper).length).toBeGreaterThan(0)
  })
})

describe('RankingView — escolha a partir de /ranking', () => {
  it('sem campus lembrado: escolher um campus leva a /ranking/N, sem lembrar o campus', async () => {
    const { wrapper, router } = await montarEm('/ranking')
    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-teste="seletor-campus-opcao"]')).toHaveLength(5),
    )

    await wrapper
      .findAll('[data-teste="seletor-campus-opcao"]')
      .find((b) => b.text() === 'Gama')
      .trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/ranking/3')
    expect(linhas(wrapper).length).toBeGreaterThan(0)
    expect(usePreferenciasStore().campusId).toBeNull()
  })
})
