import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { consultarPermissao, pedirPermissao } from './permissaoLocalizacao'

const PERMISSION_DENIED = 1
const POSITION_UNAVAILABLE = 2
const TIMEOUT = 3

/** Erro da Geolocation API com as constantes que o navegador expõe. */
const erroGeo = (code) => ({ code, PERMISSION_DENIED, POSITION_UNAVAILABLE, TIMEOUT })

/**
 * Simula a Geolocation API e a Permissions API do navegador.
 * `estado` é o que a Permissions API responde (undefined: sem a API).
 */
function simularNavegador({ estado, geolocalizacao = {}, seguro } = {}) {
  vi.stubGlobal('navigator', {
    permissions:
      estado === undefined ? undefined : { query: vi.fn(async () => ({ state: estado })) },
    geolocation: geolocalizacao === null ? undefined : geolocalizacao,
  })
  if (seguro !== undefined) vi.stubGlobal('isSecureContext', seguro)
}

beforeEach(() => {
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('consultarPermissao', () => {
  it.each([
    ['prompt', 'pendente'],
    ['granted', 'concedida'],
    ['denied', 'negada'],
  ])('traduz o estado "%s" do navegador para "%s"', async (estado, esperado) => {
    simularNavegador({ estado })
    expect(await consultarPermissao()).toBe(esperado)
  })

  it('sem Permissions API (Safari antigo), a situação é desconhecida', async () => {
    simularNavegador({ estado: undefined })
    expect(await consultarPermissao()).toBe('desconhecida')
    expect(console.warn).not.toHaveBeenCalled()
  })

  it('se a consulta falhar, a situação é desconhecida e o erro fica registrado', async () => {
    vi.stubGlobal('navigator', {
      permissions: { query: vi.fn(async () => Promise.reject(new TypeError('sem suporte'))) },
      geolocation: {},
    })
    expect(await consultarPermissao()).toBe('desconhecida')
    expect(console.warn).toHaveBeenCalled()
  })

  it('um estado que o navegador não deveria devolver também é registrado', async () => {
    simularNavegador({ estado: 'estranho' })
    expect(await consultarPermissao()).toBe('desconhecida')
    expect(console.warn).toHaveBeenCalled()
  })

  it('sem Geolocation API, a localização está indisponível', async () => {
    simularNavegador({ estado: 'prompt', geolocalizacao: null })
    expect(await consultarPermissao()).toBe('indisponivel')
  })

  it('fora de HTTPS (contexto inseguro), avisa no console e não manda liberar nada', async () => {
    simularNavegador({ estado: 'denied', seguro: false })
    expect(await consultarPermissao()).toBe('inseguro')
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('HTTPS'))
  })
})

describe('pedirPermissao', () => {
  it('aciona o pedido do navegador e devolve "concedida" sem as coordenadas (RI09)', async () => {
    const getCurrentPosition = vi.fn((sucesso) =>
      sucesso({ coords: { latitude: -15.98, longitude: -48.04, accuracy: 10 } }),
    )
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    const resultado = await pedirPermissao()

    expect(getCurrentPosition).toHaveBeenCalledOnce()
    expect(resultado).toBe('concedida')
  })

  it('não pede leitura precisa nem nova: a posição é descartada', async () => {
    const getCurrentPosition = vi.fn((sucesso) => sucesso({ coords: {} }))
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    await pedirPermissao()

    expect(getCurrentPosition.mock.calls[0][2]).toMatchObject({
      enableHighAccuracy: false,
      maximumAge: Infinity,
    })
  })

  it('devolve "negada" quando a pessoa recusa e o navegador passa a bloquear', async () => {
    const getCurrentPosition = vi.fn((_sucesso, falha) => {
      navigator.permissions.query = vi.fn(async () => ({ state: 'denied' }))
      falha(erroGeo(PERMISSION_DENIED))
    })
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('negada')
  })

  it('fechar o pedido sem decidir (code 1 com a permissão ainda em "prompt") é "dispensada"', async () => {
    const getCurrentPosition = vi.fn((_sucesso, falha) => falha(erroGeo(PERMISSION_DENIED)))
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('dispensada')
  })

  it('sem Permissions API, o code 1 conta como "negada"', async () => {
    const getCurrentPosition = vi.fn((_sucesso, falha) => falha(erroGeo(PERMISSION_DENIED)))
    simularNavegador({ estado: undefined, geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('negada')
  })

  it.each([
    ['POSITION_UNAVAILABLE', POSITION_UNAVAILABLE],
    ['TIMEOUT', TIMEOUT],
  ])('%s: a permissão foi dada, mas sem sinal ("sem-sinal")', async (_nome, code) => {
    const getCurrentPosition = vi.fn((_sucesso, falha) => falha(erroGeo(code)))
    simularNavegador({ estado: 'granted', geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('sem-sinal')
  })

  it('se o navegador nunca responder, devolve "sem-resposta" depois do prazo', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const getCurrentPosition = vi.fn()
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    const pedido = pedirPermissao()
    await vi.advanceTimersByTimeAsync(30_000)

    expect(await pedido).toBe('sem-resposta')
  })

  it('uma resposta que chega depois do prazo é ignorada', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    let responder
    const getCurrentPosition = vi.fn((sucesso) => (responder = sucesso))
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    const pedido = pedirPermissao()
    await vi.advanceTimersByTimeAsync(30_000)
    responder({ coords: {} })

    expect(await pedido).toBe('sem-resposta')
  })

  it('se getCurrentPosition lançar exceção, devolve "indisponivel" e registra o erro', async () => {
    const getCurrentPosition = vi.fn(() => {
      throw new Error('quebrado')
    })
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('indisponivel')
    expect(console.warn).toHaveBeenCalled()
  })

  it('sem Geolocation API, devolve "indisponivel" sem lançar erro', async () => {
    simularNavegador({ estado: 'prompt', geolocalizacao: null })
    expect(await pedirPermissao()).toBe('indisponivel')
  })

  it('fora de HTTPS, devolve "inseguro" sem acionar o navegador', async () => {
    const getCurrentPosition = vi.fn()
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition }, seguro: false })

    expect(await pedirPermissao()).toBe('inseguro')
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })
})
