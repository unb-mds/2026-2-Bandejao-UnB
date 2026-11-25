// @vitest-environment node
// Ambiente node: o `URL` do Node aceita `import.meta.url`, e o caminho do
// arquivo não depende da pasta onde o comando é rodado.
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Service worker (public/sw.js, FE-14). Roda o arquivo de verdade com um
 * `self`, um `caches` e um `fetch` simulados: rede primeiro, cópia em cache
 * para o offline, a API nunca passa por ele e a navegação offline cai no
 * index.html guardado.
 */
const arquivo = (caminho) => fileURLToPath(new URL(`../${caminho}`, import.meta.url))
const codigo = readFileSync(arquivo('public/sw.js'), 'utf8')
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
  const abertos = []
  const caches = {
    open: vi.fn(async (nome) => {
      if (!abertos.includes(nome)) abertos.push(nome)
      return cache
    }),
    keys: vi.fn(async () => ['bandejao-antigo', ...abertos]),
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

  it('na ativação, apaga só os caches de versões antigas e assume as abas abertas', async () => {
    const { self, caches } = carregarServiceWorker()
    let espera
    ouvintes.install({ waitUntil: (p) => (espera = p) })
    await espera
    // O nome do cache atual sai do próprio sw.js: subir a versão não quebra o teste.
    const atual = caches.open.mock.calls[0][0]
    ouvintes.activate({ waitUntil: (p) => (espera = p) })
    await espera

    expect(caches.delete).toHaveBeenCalledWith('bandejao-antigo')
    expect(caches.delete).not.toHaveBeenCalledWith(atual)
    expect(self.clients.claim).toHaveBeenCalled()
  })

  it('tudo o que a instalação guarda existe no build (um 404 faria o addAll falhar inteiro)', async () => {
    const { cache } = carregarServiceWorker()
    let espera
    ouvintes.install({ waitUntil: (p) => (espera = p) })
    await espera
    // "/" e "/index.html" são o index.html da raiz; o resto vem de public/.
    const noBuild = (caminho) =>
      ['/', '/index.html'].includes(caminho) ? arquivo('index.html') : arquivo(`public${caminho}`)

    const essenciais = cache.addAll.mock.calls[0][0]
    expect(essenciais.filter((caminho) => !existsSync(noBuild(caminho)))).toEqual([])
  })

  it('a API (/api/) nunca passa pelo service worker', async () => {
    carregarServiceWorker()

    expect(await pedir('/api/ranking/1/')).toBeNull()
    expect(fetchSimulado).not.toHaveBeenCalled()
  })

  it('pedidos que não são GET e de outra origem também não', async () => {
    carregarServiceWorker()

    // Fora da API, para o teste não passar só pela regra do /api/.
    expect(await pedir('/ranking/1', { metodo: 'POST' })).toBeNull()
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

  it('resposta de erro da rede (404, 500) não vai para o cache', async () => {
    carregarServiceWorker()
    fetchSimulado.mockResolvedValue({ ok: false, status: 500, clone: () => ({ corpo: '500' }) })

    const resposta = await pedir('/assets/quebrado.js')
    await Promise.resolve()

    expect(resposta.status).toBe(500)
    expect(guardados.has(`${ORIGEM}/assets/quebrado.js`)).toBe(false)
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
