import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { lerPosicao } from './leituraPosicao'
import {
  IDADE_MAXIMA_POSICAO_MS,
  PRECISAO_MINIMA_METROS,
  TEMPO_LIMITE_LEITURA_MS,
} from '@/constants/localizacao'

/**
 * Leitura da posição para o check-in (RN03, RF12, front 4a): tempo limite,
 * precisão mínima e idade máxima. Uma leitura fora disso vale como
 * "localização não lida" e nunca chega ao backend.
 */
const AGORA = new Date(2026, 10, 9, 12, 0).getTime()
const erroGeo = (code) => ({ code, PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 })

function posicao({
  accuracy = 20,
  idadeMs = 0,
  latitude = -15.7631234,
  longitude = -47.8701234,
} = {}) {
  return {
    coords: { latitude, longitude, accuracy, altitude: 1100, speed: 0 },
    timestamp: AGORA - idadeMs,
  }
}

let getCurrentPosition

function simularGps(responder) {
  getCurrentPosition = vi.fn((ok, falha, opcoes) => responder({ ok, falha, opcoes }))
  vi.stubGlobal('navigator', { geolocation: { getCurrentPosition } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'] })
  vi.setSystemTime(AGORA)
  vi.stubGlobal('isSecureContext', true)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('lerPosicao', () => {
  it('pede a posição com o tempo limite e a idade máxima da RN03, em alta precisão', async () => {
    simularGps(({ ok }) => ok(posicao()))

    await lerPosicao()

    expect(getCurrentPosition).toHaveBeenCalledWith(expect.any(Function), expect.any(Function), {
      enableHighAccuracy: true,
      timeout: TEMPO_LIMITE_LEITURA_MS,
      maximumAge: IDADE_MAXIMA_POSICAO_MS,
    })
  })

  it('leitura boa: devolve só latitude e longitude, sem o resto da posição', async () => {
    simularGps(({ ok }) => ok(posicao()))

    const leitura = await lerPosicao()

    expect(leitura).toEqual({
      ok: true,
      coordenadas: { latitude: -15.7631234, longitude: -47.8701234 },
    })
  })

  it('aceita a precisão no limite exato', async () => {
    simularGps(({ ok }) => ok(posicao({ accuracy: PRECISAO_MINIMA_METROS })))

    expect((await lerPosicao()).ok).toBe(true)
  })

  it('precisão pior que a mínima: "precisao-baixa", sem coordenadas', async () => {
    simularGps(({ ok }) => ok(posicao({ accuracy: PRECISAO_MINIMA_METROS + 1 })))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'precisao-baixa' })
  })

  it('precisão ausente conta como baixa', async () => {
    simularGps(({ ok }) => ok(posicao({ accuracy: null })))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'precisao-baixa' })
  })

  it('posição mais velha que a idade máxima: "posicao-antiga"', async () => {
    simularGps(({ ok }) => ok(posicao({ idadeMs: IDADE_MAXIMA_POSICAO_MS + 1 })))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'posicao-antiga' })
  })

  it('aceita a posição com a idade máxima exata', async () => {
    simularGps(({ ok }) => ok(posicao({ idadeMs: IDADE_MAXIMA_POSICAO_MS })))

    expect((await lerPosicao()).ok).toBe(true)
  })

  it('coordenada que não é número: "sem-sinal"', async () => {
    simularGps(({ ok }) => ok(posicao({ latitude: Number.NaN })))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'sem-sinal' })
  })

  it('o navegador esgota o tempo: "tempo-esgotado"', async () => {
    simularGps(({ falha }) => falha(erroGeo(3)))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'tempo-esgotado' })
  })

  it('o navegador nunca responde: desiste no tempo limite da RN03', async () => {
    simularGps(() => {})

    const leitura = lerPosicao()
    await vi.advanceTimersByTimeAsync(TEMPO_LIMITE_LEITURA_MS)

    expect(await leitura).toEqual({ ok: false, motivo: 'tempo-esgotado' })
  })

  it('resposta que chega depois do tempo limite é ignorada', async () => {
    let responderTarde
    simularGps(({ ok }) => {
      responderTarde = () => ok(posicao())
    })

    const leitura = lerPosicao()
    await vi.advanceTimersByTimeAsync(TEMPO_LIMITE_LEITURA_MS)
    responderTarde()

    expect(await leitura).toEqual({ ok: false, motivo: 'tempo-esgotado' })
  })

  it('permissão negada: "negada"', async () => {
    simularGps(({ falha }) => falha(erroGeo(1)))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'negada' })
  })

  it('aparelho sem posição (localização desligada): "sem-sinal"', async () => {
    simularGps(({ falha }) => falha(erroGeo(2)))

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'sem-sinal' })
  })

  it('navegador sem Geolocation API: "indisponivel"', async () => {
    vi.stubGlobal('navigator', {})

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'indisponivel' })
  })

  it('página fora de HTTPS: "inseguro", sem pedir a posição', async () => {
    simularGps(({ ok }) => ok(posicao()))
    vi.stubGlobal('isSecureContext', false)
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'inseguro' })
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it('exceção do navegador ao pedir: "indisponivel"', async () => {
    simularGps(() => {
      throw new Error('quebrou')
    })
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    expect(await lerPosicao()).toEqual({ ok: false, motivo: 'indisponivel' })
  })
})
