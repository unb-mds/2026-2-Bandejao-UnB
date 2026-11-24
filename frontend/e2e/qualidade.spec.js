import { test, expect, GAMA } from './apoio/teste'
import { contaDoFluxo, entrar } from './apoio/contas'

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

/** Quanto a página passa da largura da janela (0: nada rola para o lado). */
const sobraNaLargura = (page) =>
  page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)

const TELAS_SEM_LOGIN = [
  '/boas-vindas',
  '/campus',
  `/campus/${GAMA.id}`,
  '/inicio',
  '/avaliacoes',
  `/ranking/${GAMA.id}`,
  '/progresso',
  '/login',
  '/cadastro',
  '/recuperar-senha',
  '/nao-existe',
]

const TELAS_COM_LOGIN = [
  `/campus/${GAMA.id}`,
  '/inicio',
  '/avaliacoes',
  `/ranking/${GAMA.id}`,
  '/progresso',
]

test.describe('RNF03 e FE-20: nenhuma tela rola para o lado', () => {
  test.beforeEach(async ({ page }) => {
    // Campus lembrado e aviso de localização já respondido: cada tela abre
    // direto, como na segunda visita.
    await page.addInitScript((campusId) => {
      localStorage.setItem(
        'bandejao:preferencias',
        JSON.stringify({ campusId, avisoLocalizacaoAdiado: true }),
      )
    }, GAMA.id)
  })

  test('sem login', async ({ page }) => {
    for (const tela of TELAS_SEM_LOGIN) {
      await page.goto(tela)
      await page.waitForLoadState('networkidle')
      expect.soft(await sobraNaLargura(page), `${tela} rola para o lado`).toBe(0)
    }
  })

  test('com login', async ({ page }, testInfo) => {
    // Só leitura: a conta do M4 entra e olha as telas, sem mudar pontos nem a
    // adesão ao ranking.
    await entrar(page, contaDoFluxo('progresso', testInfo))
    for (const tela of TELAS_COM_LOGIN) {
      await page.goto(tela)
      await page.waitForLoadState('networkidle')
      expect.soft(await sobraNaLargura(page), `${tela} rola para o lado`).toBe(0)
    }
  })
})
