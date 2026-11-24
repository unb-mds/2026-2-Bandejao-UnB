import { test, expect, GAMA } from './apoio/teste'
import { contaDoFluxo, entrar } from './apoio/contas'

/** A lista do ranking ou o estado vazio: o ranking do campus terminou de carregar. */
const rankingCarregado = (page) =>
  page.locator('[data-teste="ranking-lista"]').or(page.getByText('Ninguém no ranking ainda'))

/**
 * M4: previsão da fila (RF13), progresso (RF26) e ranking do campus (RF27).
 * A previsão sai do histórico das três segundas anteriores
 * (e2e/dados/historico-fila.json); a conta tem 160 pontos no semestre e
 * ainda não participa do ranking (e2e/dados/contas.json).
 */
test('previsão da fila, patente no progresso e entrada no ranking', async ({ page }, testInfo) => {
  await page.goto(`/campus/${GAMA.id}`)
  const previsao = page.getByRole('region', { name: 'Previsão · Almoço, hoje' })
  await expect(previsao).toContainText('Pico previsto: 12h às 12h15')
  const faixas = previsao.getByRole('list', { name: 'Nível previsto da fila a cada 15 minutos' })
  const pico = faixas.getByRole('listitem').filter({ hasText: '12h às 12h15' })
  await expect(pico).toContainText('Longa')
  await expect(pico).toContainText('Pico')

  const conta = contaDoFluxo('progresso', testInfo)
  await entrar(page, conta, '/progresso')
  const patente = page.getByRole('region', { name: 'Rato de RU' })
  await expect(patente).toContainText('160 pontos')
  await expect(patente).toContainText('Faltam 290 pontos para Veterano')

  // Ranking carregado (a lista ou o estado vazio; o outro projeto pode já ter
  // entrado) antes de conferir a ausência: durante o "Carregando ranking…" ou
  // com um erro, o apelido também não apareceria.
  await page.goto(`/ranking/${GAMA.id}`)
  await expect(rankingCarregado(page)).toBeVisible()
  await expect(page.getByText(conta.apelido)).toBeHidden()

  // Só aparece no ranking quem escolhe participar (RF26.2, RI12).
  await page.goto('/progresso')
  const adesao = page.getByRole('switch', { name: 'Participar do ranking' })
  await expect(adesao).not.toBeChecked()
  await adesao.click()
  await expect(adesao).toBeChecked()

  await page.goto(`/ranking/${GAMA.id}`)
  await expect(rankingCarregado(page)).toBeVisible()
  await expect(page.getByRole('button', { name: GAMA.nome })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByText(conta.apelido)).toBeVisible()
})
