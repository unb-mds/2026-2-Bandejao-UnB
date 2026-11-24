import { test, expect, GAMA, LONGE_DO_GAMA } from './apoio/teste'
import { contaDoFluxo, entrar } from './apoio/contas'

/**
 * M2: check-in com a localização simulada (RF11, RF12, fluxo 4a). Com a
 * permissão de localização concedida, o aviso de localização (RF19) não pode
 * aparecer: a resposta automática dele fica desligada.
 */
test.use({ permissions: ['geolocation'], responderAvisoLocalizacao: false })

test.describe('no RU do Gama', () => {
  test.use({ geolocation: GAMA.ru })

  test('aviso de privacidade antes do GPS, check-in confirmado e pontos', async ({
    page,
  }, testInfo) => {
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

    // Os pontos ficaram na conta (RF24): ela começou sem nenhum.
    await page.goto('/progresso')
    await expect(page.getByText('10 pontos', { exact: true })).toBeVisible()
  })
})

// Em outro teste, com outra conta: o navegador guarda a posição lida por até
// 60 s (maximumAge da leitura), então mudar a posição no meio do mesmo teste
// devolveria a antiga.
test.describe('longe do RU', () => {
  test.use({ geolocation: LONGE_DO_GAMA })

  test('o check-in é recusado pela API e não rende pontos', async ({ page }, testInfo) => {
    await entrar(page, contaDoFluxo('longe', testInfo), `/campus/${GAMA.id}`)
    const checkin = page.getByRole('region', { name: 'Check-in · Almoço' })

    await checkin.getByRole('button', { name: 'Estou no RU' }).click()

    // A API confere o raio do RU: as coordenadas vão só no corpo do POST.
    await expect(checkin).toContainText('Não foi possível confirmar que você está no RU.')
    await expect(checkin.getByRole('status')).toHaveCount(0)
    await expect(page.getByText('+10 pontos')).toBeHidden()
  })
})
