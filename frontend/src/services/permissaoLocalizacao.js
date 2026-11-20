/**
 * Permissão de localização do navegador (RF19).
 *
 * Só trata da permissão: a leitura com os critérios da RN03 fica com quem
 * usa a posição (detecção de campus e check-in). As coordenadas recebidas
 * ao pedir a permissão são descartadas na hora (RI09).
 *
 * Situações devolvidas: 'pendente' (o navegador ainda pode perguntar),
 * 'concedida', 'negada' (o navegador bloqueou) e 'indisponivel' (sem GPS).
 */

const ESTADOS = { prompt: 'pendente', granted: 'concedida', denied: 'negada' }

function geolocalizacao() {
  return globalThis.navigator?.geolocation ?? null
}

export async function consultarPermissao() {
  if (!geolocalizacao()) return 'indisponivel'
  try {
    const { state } = await globalThis.navigator.permissions.query({ name: 'geolocation' })
    return ESTADOS[state] ?? 'pendente'
  } catch {
    // Sem Permissions API (Safari antigo): só se sabe perguntando.
    return 'pendente'
  }
}

export function pedirPermissao() {
  const geo = geolocalizacao()
  if (!geo) return Promise.resolve('indisponivel')
  return new Promise((resolver) => {
    geo.getCurrentPosition(
      () => resolver('concedida'),
      // Tempo esgotado ou GPS sem sinal não são recusa: a permissão foi dada.
      (erro) => resolver(erro.code === erro.PERMISSION_DENIED ? 'negada' : 'concedida'),
      { timeout: 5000 },
    )
  })
}
