import { test, expect, GAMA } from './apoio/teste'
import { contaDoFluxo, entrar } from './apoio/contas'

/**
 * FE-16 (checklist de qualidade, QA-07): o que dá para conferir sozinho, no
 * celular (360 px) e no desktop, com o Chromium do Playwright. Firefox e
 * Safari não rodam aqui, e as versões de marca do Chrome e do Edge ficam no
 * checklist manual, docs/qualidade/checklist-qualidade-front.md.
 */

/** Um prato do almoço de segunda do Gama (e2e/dados/cardapio.json). */
const PRATO_DO_GAMA = 'Silveirinha de carne'

const cardapioDoGama = (page) =>
  page
    .getByRole('region', { name: 'Cardápio' })
    .getByRole('listitem')
    .filter({ hasText: PRATO_DO_GAMA })

// Cada toque é conferido pela tela que ele abre: um passo a mais ou a menos
// falha no passo certo. O aviso de localização (RF19) conta como interação
// (RNF03), então a resposta automática do apoio fica desligada.
test.describe('RNF03: interações até o cardápio na primeira visita', () => {
  test.use({ responderAvisoLocalizacao: false })

  // A Release 2 conta 2 interações sem permissão ("Agora não" e o campus). O
  // "Continuar sem login" que havia no meio saiu da boas-vindas (#285).
  test('sem permitir a localização: "Agora não" e o campus (2); na visita seguinte, nenhuma', async ({
    page,
  }) => {
    await page.goto('/')
    const aviso = page.getByRole('dialog', { name: 'Usar sua localização?' })
    await aviso.getByRole('button', { name: 'Agora não' }).click()
    await expect(aviso).toBeHidden()
    await expect(page).toHaveURL(/\/boas-vindas$/)
    await expect(page.getByRole('link', { name: 'Continuar sem login' })).toHaveCount(0)

    await page.getByRole('button', { name: new RegExp(GAMA.nome) }).click()
    await expect(page).toHaveURL(new RegExp(`/campus/${GAMA.id}$`))
    await expect(cardapioDoGama(page)).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)

    // Visita seguinte (RNF03, RN04): o campus fica lembrado no aparelho e o
    // cardápio abre sem interação, sem o aviso por cima.
    await page.goto('/')
    await expect(page).toHaveURL(new RegExp(`/campus/${GAMA.id}$`))
    await expect(cardapioDoGama(page)).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  test.describe('com a localização permitida', () => {
    test.use({ geolocation: GAMA.ru })

    // Pendência do EXTRA 3: sem a detecção do campus (RF20.1, FE-E3),
    // permitir a localização não leva ao cardápio do campus em que a pessoa
    // está. Quando a FE-E3 entrar, este teste passa a passar e o test.fail()
    // acusa, para o checklist ser atualizado.
    test.fail(
      '"Permitir localização" e o pedido do navegador (2) abrem o cardápio do campus detectado',
      async ({ page, context }) => {
        await page.goto('/')
        const aviso = page.getByRole('dialog', { name: 'Usar sua localização?' })
        // O Playwright não toca no pedido nativo do navegador: a permissão é
        // dada antes do toque, e o pedido conta +1, como faria a pessoa.
        await context.grantPermissions(['geolocation'])
        await aviso.getByRole('button', { name: 'Permitir localização' }).click()

        await expect(cardapioDoGama(page)).toBeVisible()
      },
    )
  })
})

/**
 * Elementos que passam da largura da janela. O documento não serve de
 * medida: o `.app` corta o que passa (`overflow: hidden`) e o `.conteudo` rola
 * sozinho, então a página nunca fica mais larga que a janela. As faixas que
 * rolam para o lado de propósito são marcadas com `data-rolagem-horizontal`.
 */
const elementosQuePassam = (page) =>
  page.evaluate(() => {
    const largura = document.documentElement.clientWidth
    return [...document.querySelectorAll('body *')]
      .filter((el) => !el.closest('[data-rolagem-horizontal]'))
      .filter((el) => {
        const caixa = el.getBoundingClientRect()
        return caixa.width > 0 && caixa.right > largura + 1
      })
      .map((el) => `${el.tagName.toLowerCase()}.${el.getAttribute('class') ?? ''}`)
  })

const titulo = (nome) => (page) => page.getByRole('heading', { level: 1, name: nome })
const rankingCarregado = (page) =>
  page.locator('[data-teste="ranking-lista"]').or(page.getByText('Ninguém no ranking ainda'))

// Cada tela só é medida depois de o conteúdo dela aparecer: uma tela de erro
// ou de carregamento, mais curta, passaria sem provar nada.
const TELAS_SEM_LOGIN = [
  {
    rota: '/boas-vindas',
    pronta: (page) => page.getByRole('button', { name: new RegExp(GAMA.nome) }),
  },
  { rota: '/campus', pronta: (page) => page.getByRole('button', { name: new RegExp(GAMA.nome) }) },
  { rota: `/campus/${GAMA.id}`, pronta: cardapioDoGama },
  { rota: '/inicio', pronta: (page) => page.getByText('Ver cardápio completo') },
  {
    rota: '/avaliacoes',
    pronta: (page) => page.getByRole('region', { name: 'Avaliações da refeição' }),
  },
  { rota: `/ranking/${GAMA.id}`, pronta: rankingCarregado },
  { rota: '/progresso', pronta: (page) => page.getByText('Entre para ver seu progresso') },
  { rota: '/login', pronta: (page) => page.getByRole('textbox', { name: 'E-mail institucional' }) },
  { rota: '/cadastro', pronta: titulo('Criar conta') },
  { rota: '/confirmar-email', pronta: titulo('Confirmar e-mail') },
  { rota: '/recuperar-senha', pronta: titulo('Recuperar senha') },
  { rota: '/redefinir-senha', pronta: titulo('Redefinir senha') },
  { rota: '/nao-existe', pronta: titulo('Página não encontrada') },
]

test.describe('RNF03 e FE-20: nenhuma tela passa da largura da janela', () => {
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

  test('controle: o detector acusa um elemento mais largo que a janela', async ({ page }) => {
    await page.goto(`/campus/${GAMA.id}`)
    await expect(cardapioDoGama(page)).toBeVisible()
    expect(await elementosQuePassam(page)).toEqual([])

    await page
      .locator('.conteudo')
      .first()
      .evaluate((conteudo) => {
        const largo = document.createElement('div')
        largo.className = 'largo-de-proposito'
        largo.style.width = '2000px'
        conteudo.append(largo)
      })
    expect(await elementosQuePassam(page)).toContain('div.largo-de-proposito')
  })

  test('sem login', async ({ page }) => {
    for (const { rota, pronta } of TELAS_SEM_LOGIN) {
      await page.goto(rota)
      await expect(pronta(page), `${rota} não carregou`).toBeVisible()
      expect.soft(await elementosQuePassam(page), `${rota} passa da largura`).toEqual([])
    }
  })

  test('com login', async ({ page }, testInfo) => {
    // Só leitura: entra com a conta do M4 e olha as telas, sem mudar pontos
    // nem a adesão ao ranking. O apelido em /progresso prova que a sessão
    // continua ativa.
    const conta = contaDoFluxo('progresso', testInfo)
    await entrar(page, conta)
    const telas = [
      ...TELAS_SEM_LOGIN.filter(({ rota }) =>
        [`/campus/${GAMA.id}`, '/inicio', '/avaliacoes', `/ranking/${GAMA.id}`].includes(rota),
      ),
      { rota: '/progresso', pronta: (page) => page.getByRole('banner').getByText(conta.apelido) },
    ]
    for (const { rota, pronta } of telas) {
      await page.goto(rota)
      await expect(pronta(page), `${rota} não carregou`).toBeVisible()
      expect.soft(await elementosQuePassam(page), `${rota} passa da largura`).toEqual([])
    }
  })
})

// FE-23: o que depende da largura real da janela (o jsdom não aplica as
// regras de largura, então isto fica no e2e).
test.describe('FE-23: layout do desktop', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((campusId) => {
      localStorage.setItem(
        'bandejao:preferencias',
        JSON.stringify({ campusId, avisoLocalizacaoAdiado: true }),
      )
    }, GAMA.id)
  })

  test('a lateral só aparece a partir de 1024 px, e a barra do topo de 768 a 1023 px', async ({
    page,
  }) => {
    for (const [largura, lateral, topo] of [
      [360, false, false],
      [768, false, true],
      [1023, false, true],
      [1024, true, false],
      [1366, true, false],
    ]) {
      await page.setViewportSize({ width: largura, height: 800 })
      await page.goto(`/campus/${GAMA.id}`)
      await expect(cardapioDoGama(page)).toBeVisible()
      const barraLateral = page.locator('.barra-lateral')
      const barraTopo = page.locator('.navegacao-topo')
      await (lateral ? expect(barraLateral).toBeVisible() : expect(barraLateral).toBeHidden())
      await (topo ? expect(barraTopo).toBeVisible() : expect(barraTopo).toBeHidden())
    }
  })

  test('cadastro numa janela baixa: o topo da tela continua alcançável', async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== 'desktop', 'só o desktop divide a tela de conta')
    await page.setViewportSize({ width: 1366, height: 650 })
    await page.goto('/cadastro')
    await page.getByRole('radio', { name: 'Aluno' }).click()
    await page.locator('.area-tela').evaluate((area) => area.scrollTo(0, 0))

    const voltar = await page.getByRole('button', { name: 'Voltar' }).boundingBox()
    expect(voltar.y).toBeGreaterThanOrEqual(0)
  })
})
