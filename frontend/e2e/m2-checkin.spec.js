import { test, expect, GAMA } from './apoio/teste'
import { contaDoFluxo, entrar } from './apoio/contas'

/**
 * M2: check-in com a localização simulada no RU do Gama (RF11, RF12, fluxo
 * 4a): aviso de privacidade atualizado antes do GPS, confirmação e pontos.
 */
test.use({ geolocation: GAMA.ru, permissions: ['geolocation'] })

test('check-in no RU com o aviso de privacidade antes do GPS', async ({ page }, testInfo) => {
  await entrar(page, contaDoFluxo('checkin', testInfo), `/campus/${GAMA.id}`)
  const checkin = page.getByRole('region', { name: 'Check-in · Almoço' })

  await checkin.getByRole('button', { name: 'Estou no RU' }).click()

  // A conta aceitou uma versão antiga do aviso (fixture): ele vem antes do GPS.
  const aviso = checkin.getByRole('region', { name: 'Atualizamos o aviso de privacidade' })
  await expect(aviso).toBeVisible()
  await aviso.getByRole('button', { name: 'Li e estou ciente' }).click()

  // Depois da ciência, o GPS (simulado no RU) e o POST /api/checkins/.
  await expect(checkin.getByRole('status')).toContainText('Check-in confirmado')
  await expect(page.getByText('+10 pontos')).toBeVisible()

  // Um check-in por refeição (RF12): o backend recusa o segundo.
  await page.reload()
  await checkin.getByRole('button', { name: 'Estou no RU' }).click()
  await expect(checkin).toContainText('Você já fez check-in nesta refeição hoje.')
})
