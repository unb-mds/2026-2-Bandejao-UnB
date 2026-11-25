import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { usePreferenciasStore } from '@/stores/preferencias'
import { REFEICOES } from '@/constants/refeicoes'
import { hojeISO } from '@/utils/datas'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

const SEGUNDA = (hora, minuto = 0) => new Date(2026, 8, 28, hora, minuto)
const SABADO = (hora, minuto = 0) => new Date(2026, 9, 3, hora, minuto)
const COORDENADAS = { latitude: -15.7631234, longitude: -47.8701234 }

let pinia
async function montarEm(caminho) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

function simularGps({ responderNaHora = true } = {}) {
  let responder = () => {}
  const getCurrentPosition = vi.fn((ok) => {
    const ler = () => ok({ coords: { ...COORDENADAS, accuracy: 15 }, timestamp: Date.now() })
    if (responderNaHora) ler()
    else responder = ler
  })
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn(async () => ({ state: 'granted' })) },
    geolocation: { getCurrentPosition },
  })
  return { responder: () => responder() }
}

async function entrarComAvisoAceito() {
  const auth = useAuthStore()
  await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  await auth.registrarCienciaPrivacidade()
}

function campiComo(resposta) {
  const getOriginal = apiClient.get.bind(apiClient)
  return vi
    .spyOn(apiClient, 'get')
    .mockImplementation((caminho, opcoes) =>
      caminho === '/campi/'
        ? resposta(() => getOriginal(caminho, opcoes))
        : getOriginal(caminho, opcoes),
    )
}

const semConexao = () =>
  Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
const nuncaResponde = () => new Promise(() => {})

const tituloDoCheckin = (wrapper) => wrapper.get('#titulo-checkin').text()

const checkinsEnviados = (post) =>
  post.mock.calls.filter(([caminho]) => caminho === '/checkins/').map(([, corpo]) => corpo)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA(12))
  vi.stubGlobal('isSecureContext', true)
  localStorage.clear()
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('CampusView (FE-07, front 3a.2)', () => {
  it('mostra o nome do campus vindo do GET /api/campi/', async () => {
    const { wrapper } = await montarEm('/campus/3')

    await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Gama'))
  })

  it('AvisoExecutivo só no Darcy Ribeiro (RF20.4)', async () => {
    const darcy = await montarEm('/campus/1')
    await vi.waitFor(() => expect(darcy.wrapper.find('h1').text()).toBe('Darcy Ribeiro'))
    expect(darcy.wrapper.find('[data-teste="aviso-executivo"]').exists()).toBe(true)
    darcy.wrapper.unmount()

    const gama = await montarEm('/campus/3')
    await vi.waitFor(() => expect(gama.wrapper.find('h1').text()).toBe('Gama'))
    expect(gama.wrapper.find('[data-teste="aviso-executivo"]').exists()).toBe(false)
  })

  it('cardápio e fila na mesma tela', async () => {
    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    // Na tela (main): a BarraLateral do desktop (FE-23) também diz "Fila do RU".
    expect(wrapper.get('main').text()).toContain('Fila do RU')
    expect(wrapper.get('main').text()).toContain('Entre para fazer check-in')
  })

  it('a previsão da fila aparece na tela do campus, sem login (FE-11, RF13)', async () => {
    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() =>
      expect(wrapper.findAll('[data-teste="previsao-faixa"]').length).toBeGreaterThan(0),
    )
    expect(wrapper.get('#titulo-previsao').text()).toContain('hoje')
    expect(wrapper.find('[data-teste="previsao-pico"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('A previsão de fila chega na próxima versão')
  })

  it('a previsão segue o dia e a refeição escolhidos no cardápio', async () => {
    const get = vi.spyOn(apiClient, 'get')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))

    usePreferenciasStore().selecionar('2026-09-29', 'jantar')
    await flushPromises()

    await vi.waitFor(() =>
      expect(wrapper.get('#titulo-previsao').text()).toBe('Previsão · Jantar, ter 29/09'),
    )
    expect(get.mock.calls.map(([caminho]) => caminho)).toContain(
      '/fila/previsao/?campus=1&refeicao=jantar&data=2026-09-29',
    )
  })

  it('a falha da previsão não derruba o cardápio nem o check-in', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho.startsWith('/fila/previsao/')
        ? Promise.reject(new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }))
        : getOriginal(caminho, opcoes),
    )

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('[data-teste="previsao-erro"]').exists()).toBe(true))
    expect(wrapper.find('.prato').exists()).toBe(true)
    expect(wrapper.text()).toContain('Entre para fazer check-in')
  })

  it('uma seção falhando não derruba a outra', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho.startsWith('/cardapio/')
        ? Promise.reject(new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }))
        : getOriginal(caminho, opcoes),
    )

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Não foi possível carregar o cardápio'))
    // Na tela (main): a BarraLateral do desktop (FE-23) também diz "Fila do RU".
    expect(wrapper.get('main').text()).toContain('Fila do RU')
    expect(wrapper.get('main').text()).toContain('Entre para fazer check-in')
  })

  it('a lista de campi falhando não esconde o cardápio', async () => {
    campiComo(semConexao)

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(wrapper.text()).not.toContain('Campus não encontrado')
  })

  it('lista de campi falhando: avisa, mantém o AvisoExecutivo e deixa tentar de novo', async () => {
    let falhar = true
    campiComo((real) => (falhar ? semConexao() : real()))
    const preferencias = usePreferenciasStore()

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('[data-teste="falha-campi"]').exists()).toBe(true))
    expect(wrapper.get('[data-teste="falha-campi"]').text()).toContain('Sem internet.')
    expect(wrapper.find('h1').text()).toBe('Campus')
    expect(wrapper.find('[data-teste="aviso-executivo"]').exists()).toBe(true)
    expect(wrapper.find('[data-teste="checkin-aguardando-campus"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Entre para fazer check-in')
    expect(preferencias.campusId).toBeNull()

    falhar = false
    await wrapper.get('[data-teste="falha-campi"] button').trigger('click')

    await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Darcy Ribeiro'))
    expect(wrapper.find('[data-teste="falha-campi"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Entre para fazer check-in')
    expect(preferencias.campusId).toBe(1)
  })

  it('check-in desativado enquanto a lista de campi não chega', async () => {
    campiComo(nuncaResponde)

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    expect(wrapper.find('[data-teste="checkin-aguardando-campus"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Entre para fazer check-in')
    expect(wrapper.find('[data-teste="falha-campi"]').exists()).toBe(false)
  })

  it('/campus/99 sem a lista de campi: o cardápio dizendo que o campus não existe vira "Campus não encontrado"', async () => {
    campiComo(nuncaResponde)

    const { wrapper } = await montarEm('/campus/99')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Campus não encontrado'))
    expect(wrapper.text()).not.toContain('Tentar novamente')
    expect(wrapper.find('[data-teste="checkin-aguardando-campus"]').exists()).toBe(false)
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(false)
  })

  it('campus lembrado que saiu do banco: "Campus não encontrado" e a preferência é limpa', async () => {
    const preferencias = usePreferenciasStore()
    preferencias.escolherCampus(7)

    const { wrapper } = await montarEm('/campus/7')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Campus não encontrado'))
    expect(preferencias.campusId).toBeNull()
  })

  it('link para outro campus inexistente não apaga o campus lembrado', async () => {
    const preferencias = usePreferenciasStore()
    preferencias.escolherCampus(3)

    const { wrapper } = await montarEm('/campus/99')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Campus não encontrado'))
    expect(preferencias.campusId).toBe(3)
  })

  it('"Fila" com a tela já aberta rola até a seção da fila', async () => {
    const rolar = vi.fn()
    Element.prototype.scrollIntoView = rolar
    try {
      const { wrapper, router } = await montarEm('/campus/1')
      await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
      expect(rolar).not.toHaveBeenCalled()

      await router.push('/campus/1#fila')
      await flushPromises()

      expect(rolar).toHaveBeenCalledTimes(1)
      expect(rolar.mock.contexts[0]).toBe(document.getElementById('fila'))
    } finally {
      delete Element.prototype.scrollIntoView
    }
  })

  it('abrir direto em #fila rola até a seção da fila', async () => {
    const rolar = vi.fn()
    Element.prototype.scrollIntoView = rolar
    try {
      await montarEm('/campus/1#fila')

      await vi.waitFor(() => expect(rolar).toHaveBeenCalled())
      expect(rolar.mock.contexts[0]).toBe(document.getElementById('fila'))
    } finally {
      delete Element.prototype.scrollIntoView
    }
  })

  it('a refeição do check-in: outro dia usa a refeição de agora; hoje, a selecionada', async () => {
    await entrarComAvisoAceito()
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true))
    const preferencias = usePreferenciasStore()

    preferencias.selecionar('2026-09-29', 'jantar')
    await flushPromises()
    expect(tituloDoCheckin(wrapper)).toBe(`Check-in · ${REFEICOES.almoco.rotulo}`)

    preferencias.selecionar(hojeISO(SEGUNDA(12)), 'jantar')
    await flushPromises()
    expect(tituloDoCheckin(wrapper)).toBe(`Check-in · ${REFEICOES.jantar.rotulo}`)

    preferencias.selecionar(hojeISO(SEGUNDA(12)), 'cafe')
    await flushPromises()
    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true)
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(false)
  })

  it.each([
    ['segunda 14h30, último minuto do almoço', SEGUNDA(14, 30), false],
    ['segunda 14h31, almoço encerrado', SEGUNDA(14, 31), true],
    ['sábado 12h, almoço aberto', SABADO(12), false],
  ])('%s', async (_, agora, encerrada) => {
    vi.setSystemTime(agora)
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))

    usePreferenciasStore().selecionar(hojeISO(agora), 'almoco')
    await flushPromises()

    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(encerrada)
    expect(wrapper.text().includes('Entre para fazer check-in')).toBe(!encerrada)
  })

  it('o relógio anda: a tela aberta às 14h29 encerra o almoço depois das 14h30', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA(14, 29))
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    usePreferenciasStore().selecionar(hojeISO(SEGUNDA(14, 29)), 'almoco')
    await flushPromises()
    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(false)

    vi.setSystemTime(SEGUNDA(14, 31))
    vi.advanceTimersByTime(30 * 1000)
    await flushPromises()

    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true)
  })

  it('refeição encerrada: RefeicaoEncerrada no lugar do check-in (RN05)', async () => {
    vi.setSystemTime(SEGUNDA(20))

    const { wrapper } = await montarEm('/campus/1')

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true),
    )
    expect(wrapper.text()).not.toContain('Entre para fazer check-in')
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(false)
  })

  it('às 16h: a previsão do almoço de hoje sai e a do jantar de hoje aparece (RN05)', async () => {
    vi.setSystemTime(SEGUNDA(16))
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    const preferencias = usePreferenciasStore()

    preferencias.selecionar(hojeISO(SEGUNDA(16)), 'almoco')
    await flushPromises()
    expect(wrapper.find('#titulo-previsao').exists()).toBe(false)

    preferencias.selecionar(hojeISO(SEGUNDA(16)), 'jantar')
    await flushPromises()
    await vi.waitFor(() =>
      expect(wrapper.get('#titulo-previsao').text()).toBe('Previsão · Jantar, hoje'),
    )
  })

  it.each([
    ['19h30, último minuto do jantar', SEGUNDA(19, 30), true],
    ['19h31, jantar encerrado', SEGUNDA(19, 31), false],
  ])('%s: previsão do jantar de hoje aparece? %s', async (_caso, agora, aparece) => {
    vi.setSystemTime(agora)
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))

    usePreferenciasStore().selecionar(hojeISO(agora), 'jantar')
    await flushPromises()

    expect(wrapper.find('#titulo-previsao').exists()).toBe(aparece)
  })

  it('o relógio vira com a tela aberta: a previsão do almoço sai depois das 14h30', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA(14, 30))
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))
    usePreferenciasStore().selecionar(hojeISO(SEGUNDA(14, 30)), 'almoco')
    await flushPromises()
    await vi.waitFor(() => expect(wrapper.find('#titulo-previsao').exists()).toBe(true))

    vi.setSystemTime(SEGUNDA(14, 31))
    vi.advanceTimersByTime(30 * 1000)
    await flushPromises()

    expect(wrapper.find('#titulo-previsao').exists()).toBe(false)
  })

  it('dia que já passou na semana: sem previsão', async () => {
    const QUARTA = new Date(2026, 8, 30, 12, 0)
    vi.setSystemTime(QUARTA)
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('.prato').exists()).toBe(true))

    usePreferenciasStore().selecionar('2026-09-28', 'almoco')
    await flushPromises()

    expect(wrapper.find('#titulo-previsao').exists()).toBe(false)
  })

  it('refeição encerrada: a previsão dela também sai; a de outro dia continua (RN05)', async () => {
    vi.setSystemTime(SEGUNDA(20))
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true),
    )
    usePreferenciasStore().selecionar(hojeISO(SEGUNDA(20)), 'jantar')
    await flushPromises()
    expect(wrapper.find('#titulo-previsao').exists()).toBe(false)

    usePreferenciasStore().selecionar('2026-09-29', 'almoco')
    await flushPromises()

    await vi.waitFor(() =>
      expect(wrapper.get('#titulo-previsao').text()).toBe('Previsão · Almoço, ter 29/09'),
    )
    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true)
  })

  it('o check-in usa o campus da tela e a refeição selecionada', async () => {
    simularGps()
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true))

    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    expect(checkinsEnviados(post)).toEqual([
      { campus: 1, tipoRefeicao: 'almoco', coordenadas: COORDENADAS },
    ])
    await vi.waitFor(() => expect(wrapper.text()).toContain('Check-in confirmado'))
  })

  it('check-in confirmado: o PontosAviso da raiz mostra "+10 pontos" uma vez só (RF24.2)', async () => {
    simularGps()
    await entrarComAvisoAceito()
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true))

    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    await vi.waitFor(() => expect(wrapper.find('[data-teste="pontos-aviso"]').exists()).toBe(true))
    expect(wrapper.get('[data-teste="pontos-aviso"]').text()).toContain('+10 pontos')
    expect(wrapper.text().match(/\+10 pontos/g)).toHaveLength(1)
  })

  it('trocar a refeição durante a leitura do GPS: nenhum POST com a refeição nova', async () => {
    const gps = simularGps({ responderNaHora: false })
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true))
    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    const preferencias = usePreferenciasStore()
    preferencias.selecionar(preferencias.dataSelecionada, 'jantar')
    await flushPromises()
    gps.responder()
    await flushPromises()

    expect(checkinsEnviados(post)).toEqual([])
    expect(wrapper.text()).not.toContain('Check-in confirmado')
  })

  it('a refeição encerra durante a leitura do GPS: o botão some e nenhum POST sai', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA(14, 30))
    const gps = simularGps({ responderNaHora: false })
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true))
    usePreferenciasStore().selecionar(hojeISO(SEGUNDA(14, 30)), 'almoco')
    await flushPromises()
    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    vi.setSystemTime(SEGUNDA(14, 31))
    vi.advanceTimersByTime(30 * 1000)
    await flushPromises()
    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true)
    gps.responder()
    await flushPromises()

    expect(checkinsEnviados(post)).toEqual([])
  })

  it('trocar para uma refeição já encerrada durante o GPS: nenhum POST sai', async () => {
    const gps = simularGps({ responderNaHora: false })
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const { wrapper } = await montarEm('/campus/1')
    await vi.waitFor(() => expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true))
    await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
    await flushPromises()

    usePreferenciasStore().selecionar(hojeISO(SEGUNDA(12)), 'cafe')
    await flushPromises()
    expect(wrapper.find('[data-teste="refeicao-encerrada"]').exists()).toBe(true)
    gps.responder()
    await flushPromises()

    expect(checkinsEnviados(post)).toEqual([])
  })
})

describe('CampusView — canal de contato (RNF08, FE-15)', () => {
  const contato = (wrapper) => wrapper.find('[data-teste="contato-equipe"]')

  it('visitante vê o e-mail da equipe na tela do campus, sem login', async () => {
    const { wrapper } = await montarEm('/campus/1')

    expect(contato(wrapper).exists()).toBe(true)
    expect(contato(wrapper).get('a').attributes('href')).toBe('mailto:equipe@bandejaounb.com.br')
  })

  it('logada também vê', async () => {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    expect(useAuthStore().estaAutenticado).toBe(true)
    const { wrapper } = await montarEm('/campus/1')

    expect(contato(wrapper).exists()).toBe(true)
  })

  it('no "Campus não encontrado" o contato continua lá', async () => {
    const { wrapper } = await montarEm('/campus/999')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Campus não encontrado'))

    expect(contato(wrapper).exists()).toBe(true)
  })

  it('aparece uma vez só na tela', async () => {
    const { wrapper } = await montarEm('/campus/3')

    expect(wrapper.findAll('[data-teste="contato-equipe"]')).toHaveLength(1)
  })
})
