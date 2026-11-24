import { execSync } from 'node:child_process'

/**
 * Antes de cada rodada: banco limpo e as fixtures de novo (npm run e2e:dados).
 * Os fluxos mudam o banco (check-in, avaliação, adesão ao ranking), e uma
 * segunda rodada sem isso esbarraria no "um check-in por refeição". O cache
 * também é limpo: ele guarda os contadores do limite de taxa (#123), que o
 * flush não apaga, e com o relógio do backend quase parado a janela de uma
 * hora do limite de login nunca venceria.
 * Com E2E_SEM_PREPARAR=1, os dados ficam como estão (pilha que não é a do
 * e2e/docker-compose.yml).
 */
export default function preparar() {
  if (process.env.E2E_SEM_PREPARAR) return
  execSync('npm run --silent e2e:dados', { stdio: 'inherit' })
}
