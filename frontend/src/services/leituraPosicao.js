import {
  IDADE_MAXIMA_POSICAO_MS,
  PRECISAO_MINIMA_METROS,
  TEMPO_LIMITE_LEITURA_MS,
} from '@/constants/localizacao'

/**
 * Leitura da posição com os critérios da RN03 (tempo limite, precisão
 * mínima e idade máxima, Anexo A), para o check-in (RF12, front 4a).
 *
 * Só a permissão fica em permissaoLocalizacao.js; esta leitura supõe que o
 * navegador já pode responder. Devolve:
 * - `{ ok: true, coordenadas: { latitude, longitude } }`: só os dois
 *   números, nunca o objeto da posição (precisão, altitude, velocidade...);
 * - `{ ok: false, motivo }`, com motivo 'negada', 'sem-sinal',
 *   'tempo-esgotado', 'precisao-baixa', 'posicao-antiga', 'indisponivel' ou
 *   'inseguro'. Leitura fora da RN03 equivale a "localização não lida".
 *
 * Nada aqui guarda a posição (RI09): ela vai direto para quem pediu.
 */
const falhou = (motivo) => ({ ok: false, motivo })

export function lerPosicao({
  tempoLimiteMs = TEMPO_LIMITE_LEITURA_MS,
  precisaoMinimaMetros = PRECISAO_MINIMA_METROS,
  idadeMaximaMs = IDADE_MAXIMA_POSICAO_MS,
} = {}) {
  const geo = globalThis.navigator?.geolocation
  if (!geo) return Promise.resolve(falhou('indisponivel'))
  if (globalThis.isSecureContext === false) {
    console.warn('Geolocalização exige HTTPS: o navegador recusa o pedido nesta página.')
    return Promise.resolve(falhou('inseguro'))
  }

  return new Promise((resolver) => {
    let encerrado = false
    const encerrar = (resultado) => {
      if (encerrado) return
      encerrado = true
      clearTimeout(prazo)
      resolver(resultado)
    }
    // O `timeout` da API não conta o tempo antes da resposta do navegador:
    // este prazo garante os 5 s da RN03 de qualquer jeito.
    const prazo = setTimeout(() => encerrar(falhou('tempo-esgotado')), tempoLimiteMs)

    const aoLer = ({ coords, timestamp }) => {
      const { latitude, longitude, accuracy } = coords ?? {}
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        return encerrar(falhou('sem-sinal'))
      }
      if (!Number.isFinite(accuracy) || accuracy > precisaoMinimaMetros) {
        return encerrar(falhou('precisao-baixa'))
      }
      if (!(Date.now() - timestamp <= idadeMaximaMs)) return encerrar(falhou('posicao-antiga'))
      encerrar({ ok: true, coordenadas: { latitude, longitude } })
    }

    const aoFalhar = (erro) => {
      if (erro?.code === erro?.PERMISSION_DENIED) return encerrar(falhou('negada'))
      if (erro?.code === erro?.TIMEOUT) return encerrar(falhou('tempo-esgotado'))
      encerrar(falhou('sem-sinal'))
    }

    try {
      geo.getCurrentPosition(aoLer, aoFalhar, {
        enableHighAccuracy: true,
        timeout: tempoLimiteMs,
        maximumAge: idadeMaximaMs,
      })
    } catch (falha) {
      console.warn('O navegador falhou ao ler a localização.', falha)
      encerrar(falhou('indisponivel'))
    }
  })
}
