import { test as base, expect } from '@playwright/test'

/**
 * Segunda-feira, 23/11/2026, 12h em Brasília: o mesmo instante do relógio do
 * backend (FAKETIME no e2e/docker-compose.yml). O navegador anda junto, para
 * a refeição padrão (RF07) e a janela do check-in baterem com a API.
 */
export const AGORA = new Date('2026-11-23T15:00:00Z')

/** Gama: o campus com o cardápio e o histórico da fila nas fixtures do e2e. */
export const GAMA = { id: 3, nome: 'Gama', ru: { latitude: -15.989493, longitude: -48.044024 } }

/** O RU do Darcy Ribeiro, a uns 30 km do Gama: longe do raio de confirmação. */
export const LONGE_DO_GAMA = { latitude: -15.764203, longitude: -47.870251 }

export const test = base.extend({
  // Nos fluxos sem GPS, o AvisoLocalizacao (RF19) cobre a tela no primeiro
  // acesso, e a pessoa responde "Agora não". Com a permissão concedida (M2),
  // o aviso não pode aparecer: o fluxo desliga esta resposta automática, e
  // um aviso indevido trava o teste.
  responderAvisoLocalizacao: [true, { option: true }],
  page: async ({ page, responderAvisoLocalizacao }, usar) => {
    await page.clock.install({ time: AGORA })
    if (responderAvisoLocalizacao) {
      const aviso = page.getByRole('dialog', { name: 'Usar sua localização?' })
      await page.addLocatorHandler(aviso, async () => {
        await aviso.getByRole('button', { name: 'Agora não' }).click()
      })
    }
    await usar(page)
  },
})

export { expect }
