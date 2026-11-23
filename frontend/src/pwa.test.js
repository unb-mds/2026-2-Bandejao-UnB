import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { registrarServiceWorker } from './pwa'

/**
 * Registro do service worker (FE-14, RNF05): só no build de produção, só em
 * navegador com Service Worker e depois do `load`, para não disputar a rede
 * com a primeira tela. Uma falha no registro não pode quebrar o app.
 */
let register
let aoCarregar

/** O ouvinte de `load` que o registro deixou, para disparar só o deste teste. */
function capturarLoad() {
  aoCarregar = null
  vi.spyOn(window, 'addEventListener').mockImplementation((tipo, ouvinte) => {
    if (tipo === 'load') aoCarregar = ouvinte
  })
}

const carregarPagina = () => aoCarregar?.()

function simularNavegador({ comServiceWorker = true, falhar = false } = {}) {
  register = vi.fn(() => (falhar ? Promise.reject(new Error('sem https')) : Promise.resolve({})))
  vi.stubGlobal('navigator', comServiceWorker ? { serviceWorker: { register } } : {})
}

beforeEach(() => {
  vi.stubEnv('PROD', true)
  capturarLoad()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('registrarServiceWorker', () => {
  it('em produção, registra /sw.js depois do load', () => {
    simularNavegador()

    registrarServiceWorker()
    expect(register).not.toHaveBeenCalled()
    expect(aoCarregar).toEqual(expect.any(Function))
    carregarPagina()

    expect(register).toHaveBeenCalledWith('/sw.js')
  })

  it('fora da produção (npm run dev), não registra', () => {
    vi.stubEnv('PROD', false)
    simularNavegador()

    registrarServiceWorker()
    carregarPagina()

    expect(register).not.toHaveBeenCalled()
  })

  it('navegador sem Service Worker: não faz nada e não quebra', () => {
    simularNavegador({ comServiceWorker: false })

    expect(() => {
      registrarServiceWorker()
      carregarPagina()
    }).not.toThrow()
  })

  it('registro que falha: o app continua, e a falha vai para o console como aviso', async () => {
    simularNavegador({ falhar: true })
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {})

    registrarServiceWorker()
    carregarPagina()
    await new Promise((resolver) => setTimeout(resolver))

    expect(aviso).toHaveBeenCalledTimes(1)
  })
})
