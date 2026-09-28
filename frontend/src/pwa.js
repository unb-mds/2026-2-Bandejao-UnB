/**
 * Registro do service worker (RNF05 — instalabilidade do PWA). Só em
 * produção: no `npm run dev` o cache atrapalharia o recarregamento.
 */
export function registrarServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => {
      // Sem service worker o app continua funcionando, só não fica instalável/offline.
    })
  })
}
