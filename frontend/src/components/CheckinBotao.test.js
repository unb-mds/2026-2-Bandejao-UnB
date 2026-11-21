import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import CheckinBotao from './CheckinBotao.vue'
import { useAuthStore } from '@/stores/auth'
import { useFilaStore } from '@/stores/fila'
import { apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'
import { abrirAvisoLocalizacao } from '@/composables/avisoLocalizacao'
import { PRECISAO_MINIMA_METROS, IDADE_MAXIMA_POSICAO_MS } from '@/constants/localizacao'

/**
 * Cada desfecho do fluxo 4a (FE-05): visitante, aviso de privacidade antes
 * do GPS, permissão de localização, leitura fora da RN03 e as respostas do
 * POST /api/checkins/ (201, 422 por `codigo`, 403 e 400). Integração com a
 * filaStore, o authStore e o servidor simulado; o navegador é simulado.
 */
vi.mock('@/composables/avisoLocalizacao', async (original) => ({
  ...(await original()),
  abrirAvisoLocalizacao: vi.fn(),
}))

// Segunda-feira, 09/11/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 10, 9, 12, 0)
const COORDENADAS = { latitude: -15.7631234, longitude: -47.8701234 }
const erroGeo = (code) => ({ code, PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 })

const boaLeitura = ({ ok }) =>
  ok({ coords: { ...COORDENADAS, accuracy: 15 }, timestamp: Date.now() })

let getCurrentPosition

/** `estado`: resposta da Permissions API; `aoLer`: o que o GPS devolve. */
function simularNavegador({ estado = 'granted', aoLer = boaLeitura } = {}) {
  getCurrentPosition = vi.fn((ok, falha) => aoLer({ ok, falha }))
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn(async () => ({ state: estado })) },
    geolocation: { getCurrentPosition },
  })
}

async function entrar({ comAviso = true } = {}) {
  const auth = useAuthStore()
  await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  if (comAviso) await auth.registrarCienciaPrivacidade()
  return auth
}

const montados = []
async function montar(props = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'inicio', component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  const wrapper = mount(CheckinBotao, {
    props: { campusId: 1, tipoRefeicao: 'almoco', ...props },
    global: { plugins: [router] },
    attachTo: document.body,
  })
  montados.push(wrapper)
  await flushPromises()
  return wrapper
}

async function tocarNoBotao(wrapper) {
  await wrapper.get('[data-teste="checkin-botao"]').trigger('click')
  await flushPromises()
}

const texto = (wrapper) => wrapper.text().replace(/\s+/g, ' ')

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  vi.stubGlobal('isSecureContext', true)
  localStorage.clear()
  reiniciarSimulacao()
  setActivePinia(createPinia())
  abrirAvisoLocalizacao.mockReset()
  simularNavegador()
})

afterEach(() => {
  montados.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('CheckinBotao — visitante (RF05)', () => {
  it('mostra o convite ao login no lugar do botão e não lê o GPS', async () => {
    const wrapper = await montar()

    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(false)
    expect(texto(wrapper)).toContain('Entre para fazer check-in')
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })
})

describe('CheckinBotao — aviso de privacidade antes do GPS (RF11, RNF07.1)', () => {
  it('com o aviso pendente, mostra o AvisoPrivacidade e não lê o GPS', async () => {
    await entrar({ comAviso: false })
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    const aviso = wrapper.find('[data-teste="aviso-privacidade"]')
    expect(aviso.exists()).toBe(true)
    for (const tema of ['fila', 'localização', 'pontos', 'ranking', 'Bandeja de Ouro']) {
      expect(aviso.text()).toContain(tema)
    }
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it('ao dar ciência: POST /privacidade/aceite/, depois o GPS e o check-in', async () => {
    const auth = await entrar({ comAviso: false })
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()
    await tocarNoBotao(wrapper)

    await wrapper.get('[data-teste="aviso-privacidade-ciente"]').trigger('click')
    await flushPromises()

    expect(post.mock.calls.map(([caminho]) => caminho)).toEqual([
      '/privacidade/aceite/',
      '/checkins/',
    ])
    expect(auth.avisoPrivacidadePendente).toBe(false)
    expect(texto(wrapper)).toContain('Check-in confirmado')
  })

  it('"Agora não" fecha o aviso sem ler o GPS', async () => {
    await entrar({ comAviso: false })
    const wrapper = await montar()
    await tocarNoBotao(wrapper)

    await wrapper.get('[data-teste="aviso-privacidade-agora-nao"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-teste="aviso-privacidade"]').exists()).toBe(false)
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true)
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it('se a ciência falha, mostra o erro e continua no aviso', async () => {
    await entrar({ comAviso: false })
    const wrapper = await montar()
    await tocarNoBotao(wrapper)
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    await wrapper.get('[data-teste="aviso-privacidade-ciente"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-teste="aviso-privacidade"]').text()).toContain('Sem internet.')
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it('403 aviso_privacidade_pendente do servidor: mostra o aviso de novo', async () => {
    const auth = await entrar({ comAviso: false })
    // A sessão do PWA diz que não há aviso, mas o servidor discorda.
    auth.usuario = { ...auth.usuario, avisoPrivacidadePendente: false }
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(wrapper.find('[data-teste="aviso-privacidade"]').exists()).toBe(true)
    expect(auth.avisoPrivacidadePendente).toBe(true)
  })

  it('depois do 403, dar ciência lê o GPS de novo e confirma o check-in', async () => {
    const auth = await entrar({ comAviso: false })
    auth.usuario = { ...auth.usuario, avisoPrivacidadePendente: false }
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()
    await tocarNoBotao(wrapper)

    await wrapper.get('[data-teste="aviso-privacidade-ciente"]').trigger('click')
    await flushPromises()

    expect(post.mock.calls.map(([caminho]) => caminho)).toEqual([
      '/checkins/',
      '/privacidade/aceite/',
      '/checkins/',
    ])
    expect(getCurrentPosition).toHaveBeenCalledTimes(2)
    expect(texto(wrapper)).toContain('Check-in confirmado')
  })
})

describe('CheckinBotao — permissão de localização (RF19)', () => {
  it('navegador sem Permissions API, nunca permitido: abre o AvisoLocalizacao', async () => {
    getCurrentPosition = vi.fn((ok) => boaLeitura({ ok }))
    vi.stubGlobal('navigator', { geolocation: { getCurrentPosition } })
    abrirAvisoLocalizacao.mockResolvedValue('concedida')
    await entrar()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(abrirAvisoLocalizacao).toHaveBeenCalledOnce()
    expect(texto(wrapper)).toContain('Check-in confirmado')
  })

  it.each([
    ['inseguro', 'endereço seguro (https://)'],
    ['indisponivel', 'Este navegador não oferece localização'],
  ])('desfecho %s: mostra a mensagem e não envia', async (desfecho, trecho) => {
    simularNavegador({ estado: 'prompt' })
    abrirAvisoLocalizacao.mockResolvedValue(desfecho)
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain(trecho)
    expect(post).not.toHaveBeenCalled()
  })

  it('permissão ainda não pedida: abre o AvisoLocalizacao antes de ler', async () => {
    simularNavegador({ estado: 'prompt' })
    abrirAvisoLocalizacao.mockResolvedValue('concedida')
    await entrar()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(abrirAvisoLocalizacao).toHaveBeenCalledOnce()
    expect(getCurrentPosition).toHaveBeenCalledOnce()
    expect(texto(wrapper)).toContain('Check-in confirmado')
  })

  it('"Agora não" no AvisoLocalizacao: não lê nem envia nada', async () => {
    simularNavegador({ estado: 'prompt' })
    abrirAvisoLocalizacao.mockResolvedValue('adiado')
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(getCurrentPosition).not.toHaveBeenCalled()
    expect(post).not.toHaveBeenCalled()
    expect(texto(wrapper)).toContain('O check-in precisa da sua localização')
  })

  it('navegador bloqueou: abre o passo a passo (AvisoLocalizacao) e não envia', async () => {
    simularNavegador({ estado: 'denied' })
    abrirAvisoLocalizacao.mockResolvedValue('negada')
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(abrirAvisoLocalizacao).toHaveBeenCalledOnce()
    expect(post).not.toHaveBeenCalled()
    expect(texto(wrapper)).toContain('Libere a localização')
  })

  it('negada na hora da leitura: abre o AvisoLocalizacao e não envia', async () => {
    simularNavegador({ estado: 'granted', aoLer: ({ falha }) => falha(erroGeo(1)) })
    abrirAvisoLocalizacao.mockResolvedValue('negada')
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(abrirAvisoLocalizacao).toHaveBeenCalledOnce()
    expect(post).not.toHaveBeenCalled()
  })
})

describe('CheckinBotao — leitura fora da RN03 nunca chega ao backend', () => {
  it.each([
    [
      'precisão baixa',
      ({ ok }) =>
        ok({
          coords: { ...COORDENADAS, accuracy: PRECISAO_MINIMA_METROS + 50 },
          timestamp: Date.now(),
        }),
      'precisão suficiente',
    ],
    [
      'posição antiga',
      ({ ok }) =>
        ok({
          coords: { ...COORDENADAS, accuracy: 10 },
          timestamp: Date.now() - IDADE_MAXIMA_POSICAO_MS - 1000,
        }),
      'desatualizada',
    ],
    ['tempo esgotado', ({ falha }) => falha(erroGeo(3)), 'a tempo'],
    ['sem sinal', ({ falha }) => falha(erroGeo(2)), 'localização do aparelho'],
  ])('%s: mostra o motivo e não envia', async (_caso, aoLer, trecho) => {
    simularNavegador({ aoLer })
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(post).not.toHaveBeenCalled()
    expect(texto(wrapper)).toContain(trecho)
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true)
  })
})

describe('CheckinBotao — respostas do POST /api/checkins/', () => {
  it('201: confirma o check-in e esconde o botão', async () => {
    await entrar()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('Check-in confirmado')
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(false)
  })

  it('201 com pontos zerados (até a BE-14): não mostra "+N pontos"', async () => {
    await entrar()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).not.toMatch(/\+\d+ pontos/)
  })

  it('201 com pontos: mostra "+N pontos"', async () => {
    await entrar()
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      checkin: { id: 7, campus: 1, tipoRefeicao: 'almoco', data: '2026-11-09' },
      pontos: { total: 10, contribuicao: 10, avaliacaoLiberada: 0 },
    })
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('+10 pontos')
  })

  it('422 fora_do_horario: mostra a mensagem com o horário da refeição', async () => {
    vi.setSystemTime(new Date(2026, 10, 9, 16, 0))
    await entrar()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('O check-in do almoço só vale das 11h00 às 14h30.')
  })

  it('422 checkin_duplicado: avisa que já fez check-in', async () => {
    await entrar()
    await useFilaStore().confirmarCheckin({
      campusId: 1,
      tipoRefeicao: 'almoco',
      coordenadas: COORDENADAS,
    })
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('Você já fez check-in nesta refeição hoje.')
  })

  it('422 localizacao_nao_confirmada: avisa que não confirmou a presença no RU', async () => {
    await entrar()
    simulacao.definirLocalizacaoConfirmada(false)
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('Não foi possível confirmar que você está no RU.')
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true)
  })

  it('400 dados_invalidos: erro do aplicativo, sem mandar tentar de novo', async () => {
    simularNavegador({
      aoLer: ({ ok }) =>
        ok({ coords: { latitude: 95, longitude: -47.87, accuracy: 10 }, timestamp: Date.now() }),
    })
    await entrar()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('por um problema no aplicativo')
    expect(texto(wrapper)).not.toContain('Tente de novo')
  })

  it('401 (sessão perdida no meio): volta ao convite ao login', async () => {
    await entrar()
    simulacao.expirarSessao()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)

    expect(texto(wrapper)).toContain('Entre para fazer check-in')
  })

  it('o botão fica desativado enquanto lê o GPS e envia', async () => {
    let responder
    simularNavegador({ aoLer: (callbacks) => (responder = () => boaLeitura(callbacks)) })
    await entrar()
    const wrapper = await montar()

    await tocarNoBotao(wrapper)
    const botao = wrapper.get('[data-teste="checkin-botao"]')
    expect(botao.attributes('disabled')).toBeDefined()
    expect(botao.attributes('aria-busy')).toBe('true')

    responder()
    await flushPromises()
    expect(texto(wrapper)).toContain('Check-in confirmado')
  })

  it('trocar de refeição durante a leitura: descarta o fluxo antigo, sem POST', async () => {
    let responder
    simularNavegador({ aoLer: (callbacks) => (responder = () => boaLeitura(callbacks)) })
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()
    await tocarNoBotao(wrapper)

    await wrapper.setProps({ tipoRefeicao: 'jantar' })
    responder()
    await flushPromises()

    expect(post).not.toHaveBeenCalled()
    expect(texto(wrapper)).not.toContain('Check-in confirmado')
    const botao = wrapper.get('[data-teste="checkin-botao"]')
    expect(botao.attributes('disabled')).toBeUndefined()
    expect(botao.text()).toContain('Estou no RU')
  })

  it('trocar de campus com o POST em andamento: a resposta antiga não mexe na tela', async () => {
    await entrar()
    let liberar
    vi.spyOn(apiClient, 'post').mockImplementationOnce(
      () =>
        new Promise((resolver) => {
          liberar = () =>
            resolver({
              checkin: { id: 9, campus: 1, tipoRefeicao: 'almoco', data: '2026-11-09' },
              pontos: { total: 5 },
            })
        }),
    )
    const wrapper = await montar()
    await tocarNoBotao(wrapper)

    await wrapper.setProps({ campusId: 3 })
    liberar()
    await flushPromises()

    expect(texto(wrapper)).not.toContain('Check-in confirmado')
    expect(wrapper.get('[data-teste="checkin-botao"]').attributes('disabled')).toBeUndefined()
  })

  it('erro inesperado no meio do fluxo: o botão não fica travado', async () => {
    await entrar()
    const wrapper = await montar()
    vi.spyOn(useFilaStore(), 'confirmarCheckin').mockRejectedValueOnce(new Error('inesperado'))

    await tocarNoBotao(wrapper)

    const botao = wrapper.get('[data-teste="checkin-botao"]')
    expect(botao.attributes('disabled')).toBeUndefined()
    expect(botao.text()).toContain('Estou no RU')
  })

  it('trocar de refeição volta ao botão inicial', async () => {
    vi.setSystemTime(new Date(2026, 10, 9, 16, 0))
    await entrar()
    const wrapper = await montar()
    await tocarNoBotao(wrapper)

    await wrapper.setProps({ tipoRefeicao: 'jantar' })

    expect(texto(wrapper)).not.toContain('só vale')
    expect(wrapper.find('[data-teste="checkin-botao"]').exists()).toBe(true)
  })
})
