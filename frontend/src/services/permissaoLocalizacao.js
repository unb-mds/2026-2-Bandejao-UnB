/**
 * Permissão de localização do navegador (RF19).
 *
 * Só trata da permissão: a leitura com os critérios da RN03 (tempo limite,
 * precisão mínima e idade máxima do Anexo A) fica com quem usa a posição, a
 * detecção de campus e o check-in. A posição recebida ao pedir a permissão é
 * descartada na hora (RI09).
 *
 * consultarPermissao() devolve:
 * - 'pendente': o navegador ainda pode perguntar;
 * - 'concedida' ou 'negada' (o navegador bloqueou o site);
 * - 'desconhecida': navegador sem Permissions API (ou consulta que falhou);
 *   só se sabe perguntando;
 * - 'indisponivel': navegador sem Geolocation API;
 * - 'inseguro': página fora de HTTPS, onde o navegador sempre recusa.
 */

/** Prazo para o navegador responder ao pedido (o timeout da API só conta depois da permissão). */
export const PRAZO_RESPOSTA_MS = 30_000

/**
 * Tempo limite da leitura feita só para disparar o pedido. Não é o tempo
 * limite da RN03: a posição desta leitura é descartada.
 */
const TEMPO_LEITURA_MS = 10_000

const ESTADOS = { prompt: 'pendente', granted: 'concedida', denied: 'negada' }

function emContextoInseguro() {
  if (globalThis.isSecureContext !== false) return false
  console.warn('Geolocalização exige HTTPS: o navegador recusa o pedido nesta página.')
  return true
}

function geolocalizacao() {
  return globalThis.navigator?.geolocation ?? null
}

export async function consultarPermissao() {
  if (!geolocalizacao()) return 'indisponivel'
  if (emContextoInseguro()) return 'inseguro'

  const permissoes = globalThis.navigator.permissions
  if (typeof permissoes?.query !== 'function') return 'desconhecida'
  try {
    const { state } = await permissoes.query({ name: 'geolocation' })
    if (state in ESTADOS) return ESTADOS[state]
    console.warn('Estado inesperado da permissão de localização:', state)
  } catch (falha) {
    console.warn('Não foi possível consultar a permissão de localização.', falha)
  }
  return 'desconhecida'
}

/**
 * Aciona o pedido do navegador. Devolve:
 * - 'concedida';
 * - 'sem-sinal': permitida, mas o aparelho não deu posição (localização
 *   desligada no sistema, modo avião, sem sinal);
 * - 'negada': a pessoa recusou e o navegador passou a bloquear;
 * - 'dispensada': o pedido foi fechado sem decisão (a permissão segue em
 *   "Perguntar");
 * - 'sem-resposta': o navegador não respondeu dentro do prazo;
 * - 'indisponivel' ou 'inseguro', como em consultarPermissao().
 */
export function pedirPermissao({ prazoMs = PRAZO_RESPOSTA_MS } = {}) {
  const geo = geolocalizacao()
  if (!geo) return Promise.resolve('indisponivel')
  if (emContextoInseguro()) return Promise.resolve('inseguro')

  return new Promise((resolver) => {
    let encerrado = false
    const encerrar = (resultado) => {
      if (encerrado) return
      encerrado = true
      clearTimeout(prazo)
      resolver(resultado)
    }
    const prazo = setTimeout(() => encerrar('sem-resposta'), prazoMs)

    const aoFalhar = async (erro) => {
      if (encerrado) return
      if (erro.code !== erro.PERMISSION_DENIED) return encerrar('sem-sinal')
      // No Chrome, fechar o pedido sem decidir também chega como PERMISSION_DENIED.
      const estado = await consultarPermissao()
      encerrar(estado === 'pendente' ? 'dispensada' : 'negada')
    }

    try {
      geo.getCurrentPosition(() => encerrar('concedida'), aoFalhar, {
        enableHighAccuracy: false,
        maximumAge: Infinity,
        timeout: TEMPO_LEITURA_MS,
      })
    } catch (falha) {
      console.warn('O navegador falhou ao pedir a localização.', falha)
      encerrar('indisponivel')
    }
  })
}
