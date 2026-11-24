import { test as base, expect } from '@playwright/test'

/**
 * Segunda-feira, 23/11/2026, 12h em Brasília: o mesmo instante do relógio do
 * backend (FAKETIME no e2e/docker-compose.yml). O navegador anda junto, para
 * a refeição padrão (RF07) e a janela do check-in baterem com a API.
 */
export const AGORA = new Date('2026-11-23T15:00:00Z')

/** Gama: o campus com o cardápio e o histórico da fila nas fixtures do e2e. */
export const GAMA = { id: 3, nome: 'Gama', ru: { latitude: -15.989493, longitude: -48.044024 } }

export const test = base.extend({
  page: async ({ page }, usar) => {
    await page.clock.install({ time: AGORA })
    // No primeiro acesso sem permissão de localização, o AvisoLocalizacao
    // (RF19) cobre a tela. Nos fluxos que não usam o GPS, a pessoa responde
    // "Agora não", como faria no app.
    const aviso = page.getByRole('dialog', { name: 'Usar sua localização?' })
    await page.addLocatorHandler(aviso, async () => {
      await aviso.getByRole('button', { name: 'Agora não' }).click()
    })
    await usar(page)
  },
})

export { expect }
