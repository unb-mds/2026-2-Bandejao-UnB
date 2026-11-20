import { afterEach, describe, expect, it, vi } from 'vitest'
import { consultarPermissao, pedirPermissao } from './permissaoLocalizacao'

/** Simula a Geolocation API e a Permissions API do navegador. */
function simularNavegador({ estado, geolocalizacao = {} } = {}) {
  vi.stubGlobal('navigator', {
    permissions:
      estado === undefined ? undefined : { query: vi.fn(async () => ({ state: estado })) },
    geolocation: geolocalizacao === null ? undefined : geolocalizacao,
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
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

  it('sem Permissions API (Safari antigo), considera pendente', async () => {
    simularNavegador({ estado: undefined })
    expect(await consultarPermissao()).toBe('pendente')
  })

  it('se a consulta falhar, considera pendente', async () => {
    vi.stubGlobal('navigator', {
      permissions: { query: vi.fn(async () => Promise.reject(new TypeError('sem suporte'))) },
      geolocation: {},
    })
    expect(await consultarPermissao()).toBe('pendente')
  })

  it('sem Geolocation API, a localização está indisponível', async () => {
    simularNavegador({ estado: 'prompt', geolocalizacao: null })
    expect(await consultarPermissao()).toBe('indisponivel')
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

  it('devolve "negada" quando a pessoa recusa no navegador', async () => {
    const getCurrentPosition = vi.fn((_sucesso, falha) =>
      falha({ code: 1, PERMISSION_DENIED: 1 }),
    )
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('negada')
  })

  it('tempo esgotado ou GPS indisponível não são recusa: a permissão foi dada', async () => {
    const getCurrentPosition = vi.fn((_sucesso, falha) => falha({ code: 3, PERMISSION_DENIED: 1 }))
    simularNavegador({ estado: 'prompt', geolocalizacao: { getCurrentPosition } })

    expect(await pedirPermissao()).toBe('concedida')
  })

  it('sem Geolocation API, devolve "indisponivel" sem lançar erro', async () => {
    simularNavegador({ estado: 'prompt', geolocalizacao: null })
    expect(await pedirPermissao()).toBe('indisponivel')
  })
})
