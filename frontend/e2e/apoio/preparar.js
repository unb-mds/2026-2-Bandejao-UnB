import { execSync } from 'node:child_process'
import { MAILPIT } from './mailpit'

/**
 * Antes de cada rodada:
 * - recria o backend (npm run e2e:relogio): o relógio dele começa no almoço
 *   de 23/11 a cada subida e anda em tempo real, e uma pilha no ar há mais de
 *   2h30 já estaria fora do horário do almoço;
 * - banco limpo e as fixtures de novo (npm run e2e:dados): os fluxos mudam o
 *   banco (check-in, avaliação, adesão ao ranking), e uma segunda rodada sem
 *   isso esbarraria no "um check-in por refeição". O cache também é limpo: ele
 *   guarda os contadores do limite de taxa (#123), que o flush não apaga, e no
 *   e2e todo pedido conta como o IP do Caddy (NUM_PROXIES 0), então o limite
 *   de 60 logins por hora estouraria em poucas rodadas seguidas;
 * - a caixa do Mailpit vazia, para o M1 não achar um e-mail de outra rodada.
 *
 * Com E2E_SEM_PREPARAR=1, nada disso roda (pilha que não é a do
 * e2e/docker-compose.yml).
 */
export default async function preparar() {
  if (process.env.E2E_SEM_PREPARAR === '1') return
  execSync('npm run --silent e2e:relogio', { stdio: 'inherit' })
  execSync('npm run --silent e2e:dados', { stdio: 'inherit' })
  const resposta = await fetch(`${MAILPIT}/api/v1/messages`, { method: 'DELETE' })
  if (!resposta.ok) throw new Error(`Mailpit não limpou a caixa: HTTP ${resposta.status}`)
}
