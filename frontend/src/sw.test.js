import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import process from 'node:process'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Service worker (public/sw.js, FE-14). Roda o arquivo de verdade com um
 * `self`, um `caches` e um `fetch` simulados: rede primeiro, cópia em cache
 * para o offline, a API nunca passa por ele e a navegação offline cai no
 * index.html guardado.
 */
// O Vitest roda com a raiz em frontend/ (vitest.config.js).
const codigo = readFileSync(resolve(process.cwd(), 'public/sw.js'), 'utf8')
const ORIGEM = 'https://bandejaounb.com.br'

let ouvintes
let guardados
let fetchSimulado

function carregarServiceWorker() {
  ouvintes = {}
  guardados = new Map()
  const cache = {
    addAll: vi.fn(async (urls) =>
      urls.forEach((u) => guardados.set(new URL(u, ORIGEM).href, 'pre')),
    ),
    put: vi.fn(async (pedido, resposta) => guardados.set(pedido.url, resposta)),
  }
  const caches = {
    open: vi.fn(async () => cache),
    keys: vi.fn(async () => ['bandejao-v0', 'bandejao-v1']),
    delete: vi.fn(async () => true),
    match: vi.fn(async (pedido) => {
      const url = typeof pedido === 'string' ? new URL(pedido, ORIGEM).href : pedido.url
      return guardados.get(url) ?? undefined
    }),
  }
  const self = {
    location: new URL(`${ORIGEM}/sw.js`),
    addEventListener: (tipo, ouvinte) => (ouvintes[tipo] = ouvinte),
    skipWaiting: vi.fn(),
    clients: { claim: vi.fn() },
  }
  new Function('self', 'caches', 'fetch', 'Response', codigo)(self, caches, fetchSimulado, {
    error: () => 'erro-de-rede',
  })
  return { self, caches, cache }
}

/** Dispara um `fetch` no service worker e devolve a resposta (ou null, se ele não respondeu). */
async function pedir(caminho, { metodo = 'GET', modo = 'cors', origem = ORIGEM } = {}) {
  let resposta = null
  const evento = {
    request: { url: new URL(caminho, origem).href, method: metodo, mode: modo },
    respondWith: (promessa) => (resposta = promessa),
  }
  ouvintes.fetch(evento)
  return resposta === null ? null : await resposta
}

const respostaOk = (corpo) => ({ ok: true, corpo, clone: () => ({ corpo }) })

beforeEach(() => {
  fetchSimulado = vi.fn(async () => respostaOk('da-rede'))
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('sw.js', () => {
  it('na instalação, guarda o essencial para abrir offline e assume na hora', async () => {
    const { self, cache } = carregarServiceWorker()
    let espera
    ouvintes.install({ waitUntil: (p) => (espera = p) })
    await espera

    expect(cache.addAll).toHaveBeenCalledWith(expect.arrayContaining(['/', '/index.html']))
    expect(self.skipWaiting).toHaveBeenCalled()
  })

  it('na ativação, apaga caches de versões antigas', async () => {
    const { caches } = carregarServiceWorker()
    let espera
    ouvintes.activate({ waitUntil: (p) => (espera = p) })
    await espera

    expect(caches.delete).toHaveBeenCalledWith('bandejao-v0')
    expect(caches.delete).not.toHaveBeenCalledWith('bandejao-v1')
  })

  it('a API (/api/) nunca passa pelo service worker', async () => {
    carregarServiceWorker()

    expect(await pedir('/api/ranking/1/')).toBeNull()
    expect(fetchSimulado).not.toHaveBeenCalled()
  })

  it('pedidos que não são GET e de outra origem também não', async () => {
    carregarServiceWorker()

    expect(await pedir('/api/avaliacoes/', { metodo: 'POST' })).toBeNull()
    expect(await pedir('/css2', { origem: 'https://fonts.googleapis.com' })).toBeNull()
  })

  it('com rede: responde da rede e guarda uma cópia', async () => {
    carregarServiceWorker()

    const resposta = await pedir('/assets/index-abc.js')

    expect(resposta.corpo).toBe('da-rede')
    await vi.waitFor(() =>
      expect(guardados.get(`${ORIGEM}/assets/index-abc.js`)).toEqual({ corpo: 'da-rede' }),
    )
  })

  it('sem rede: um arquivo já guardado sai do cache', async () => {
    carregarServiceWorker()
    await pedir('/assets/index-abc.js')
    fetchSimulado.mockRejectedValue(new TypeError('offline'))

    expect(await pedir('/assets/index-abc.js')).toEqual({ corpo: 'da-rede' })
  })

  it('sem rede: uma rota do app (navegação) cai no index.html guardado', async () => {
    carregarServiceWorker()
    let espera
    ouvintes.install({ waitUntil: (p) => (espera = p) })
    await espera
    fetchSimulado.mockRejectedValue(new TypeError('offline'))

    expect(await pedir('/ranking/3', { modo: 'navigate' })).toBe('pre')
  })

  it('sem rede e sem cópia: erro de rede, sem inventar resposta', async () => {
    carregarServiceWorker()
    fetchSimulado.mockRejectedValue(new TypeError('offline'))

    expect(await pedir('/assets/nao-guardado.js')).toBe('erro-de-rede')
  })
})
