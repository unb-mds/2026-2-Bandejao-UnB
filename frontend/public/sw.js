/*
 * Service worker do Bandejão (RNF05). Estratégia simples:
 * - navegação e arquivos do app: rede primeiro, cache como reserva offline;
 * - chamadas à API (/api/) nunca são cacheadas aqui — o cache de dados é
 *   responsabilidade das stores e do backend (RNF02).
 */
const CACHE = 'bandejao-v1'
const ESSENCIAIS = ['/', '/index.html', '/manifest.webmanifest', '/icone.svg']

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ESSENCIAIS)))
  self.skipWaiting()
})

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((chaves) => Promise.all(chaves.filter((c) => c !== CACHE).map((c) => caches.delete(c))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (evento) => {
  const { request } = evento
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) {
    return
  }

  evento.respondWith(
    fetch(request)
      .then((resposta) => {
        if (resposta.ok) {
          const copia = resposta.clone()
          caches.open(CACHE).then((cache) => cache.put(request, copia))
        }
        return resposta
      })
      .catch(async () => {
        const emCache = await caches.match(request)
        if (emCache) return emCache
        // Rotas do app (SPA) caem no index.html guardado.
        if (request.mode === 'navigate') return caches.match('/index.html')
        return Response.error()
      }),
  )
})
