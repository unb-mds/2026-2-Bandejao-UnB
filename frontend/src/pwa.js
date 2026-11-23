/**
 * Registro do service worker (RNF05, FE-14). Só em produção: no `npm run dev`
 * o cache atrapalharia o recarregamento. Espera o `load` para não disputar a
 * rede com a primeira tela.
 */
export function registrarServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch((falha) => {
      // Sem service worker o app continua funcionando, só sem o cache offline.
      console.warn('Não foi possível registrar o service worker.', falha)
    })
  })
}
