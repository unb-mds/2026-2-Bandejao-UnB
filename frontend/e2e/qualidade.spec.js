import { test, expect, GAMA } from './apoio/teste'

/**
 * FE-16 (checklist de qualidade, QA-07): o que dá para conferir sozinho no
 * Chromium, no celular (360 px) e no desktop. Navegadores que o Playwright
 * daqui não roda (Firefox, Safari e Edge) ficam no checklist manual,
 * docs/qualidade/checklist-qualidade-front.md.
 */

// As interações são contadas uma a uma: o aviso de localização (RF19) também
// conta (RNF03), então a resposta automática do apoio fica desligada.
test.describe('RNF03: até 3 interações até o cardápio na primeira visita', () => {
  test.use({ responderAvisoLocalizacao: false })

  test('sem permitir a localização, 3 interações; na visita seguinte, nenhuma', async ({
    page,
  }) => {
    let interacoes = 0
    const tocar = async (alvo) => {
      await alvo.click()
      interacoes += 1
    }

    await page.goto('/')
    const aviso = page.getByRole('dialog', { name: 'Usar sua localização?' })
    await tocar(aviso.getByRole('button', { name: 'Agora não' }))
    await tocar(page.getByRole('link', { name: 'Continuar sem login' }))
    await tocar(page.getByRole('button', { name: new RegExp(GAMA.nome) }))

    const cardapio = page.getByRole('region', { name: 'Cardápio' })
    await expect(cardapio.getByRole('listitem').first()).toBeVisible()
    expect(interacoes).toBeLessThanOrEqual(3)

    // Visita seguinte (RNF03, RN04): o campus fica lembrado no aparelho e o
    // cardápio abre sem interação.
    await page.goto('/')
    await expect(page).toHaveURL(new RegExp(`/campus/${GAMA.id}$`))
    await expect(cardapio.getByRole('listitem').first()).toBeVisible()
  })
})
