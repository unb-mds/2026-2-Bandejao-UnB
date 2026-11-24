import { test, expect, GAMA } from './apoio/teste'
import { contaDoFluxo, entrar } from './apoio/contas'

/**
 * M3: cardápio com filtros (RF07, RF08, RF09, ADR 0005) e avaliação da
 * refeição (RF15). O cardápio é o almoço de segunda do Gama, lido do PDF de
 * teste pelo leitor de verdade (e2e/dados/cardapio.json).
 */
test('visitante filtra o cardápio e, depois de entrar, avalia o almoço', async ({
  page,
}, testInfo) => {
  await page.goto(`/campus/${GAMA.id}`)
  const cardapio = page.getByRole('region', { name: 'Cardápio' })
  const categoria = (nome) =>
    cardapio
      .locator('section')
      .filter({ has: page.getByRole('heading', { name: nome, exact: true }) })
  const SEM_OPCAO = 'Sem opção compatível com o filtro ativo'
  await expect(cardapio.getByRole('tab', { name: /Almoço/ })).toHaveAttribute(
    'aria-selected',
    'true',
  )
  await expect(cardapio.getByText('Silveirinha de carne')).toBeVisible()
  await expect(cardapio.getByText('Macarrão temperado')).toBeVisible()

  // Marcador (RF08): a API marca a categoria em que nenhum prato serve, e o
  // prato continua na lista com o alerta "Contém".
  await cardapio.getByRole('button', { name: 'Filtros alimentares' }).click()
  const filtros = page.getByRole('dialog', { name: 'Filtros alimentares' })
  await filtros.getByRole('button', { name: 'Trigo/Glúten' }).click()
  await filtros.getByRole('button', { name: 'Aplicar' }).click()
  await expect(filtros).toBeHidden()
  await expect(cardapio).toContainText('Evitando: Trigo/Glúten')
  await expect(categoria('GUARNIÇÃO')).toContainText(SEM_OPCAO)
  await expect(categoria('PRATO PRINCIPAL PADRÃO')).not.toContainText(SEM_OPCAO)

  // Dieta (RF09): vegetariano estrito deixa de fora o prato principal padrão.
  await cardapio.getByRole('button', { name: /Filtros alimentares/ }).click()
  await filtros.getByRole('button', { name: 'Vegetariano estrito' }).click()
  await filtros.getByRole('button', { name: 'Aplicar' }).click()
  await expect(cardapio.getByText('Silveirinha de carne')).toBeHidden()
  await expect(cardapio.getByText('Silveirinha de soja')).toBeVisible()

  const conta = contaDoFluxo('avaliacao', testInfo)
  await entrar(page, conta, '/avaliacoes')
  const avaliacoes = page.getByRole('region', { name: 'Avaliações da refeição' })
  await avaliacoes.getByRole('radio', { name: '4 estrelas — Bom' }).click()
  const comentario = `Silveirinha boa (${testInfo.project.name})`
  await avaliacoes.getByRole('textbox', { name: 'Comentário opcional' }).fill(comentario)
  await avaliacoes.getByRole('button', { name: 'Enviar avaliação' }).click()

  // A conta tem check-in neste almoço (fixture), então a avaliação pontua
  // (RN09) e o PontosAviso aparece (RF24.2).
  await expect(avaliacoes).toContainText('Avaliação enviada!')
  await expect(avaliacoes).toContainText('Sua nota: 4 estrelas')
  await expect(page.getByText('+5 pontos')).toBeVisible()
  await expect(avaliacoes.getByText(comentario)).toBeVisible()
  await expect(avaliacoes.getByText(conta.apelido)).toBeVisible()
  // A média e a quantidade não entram aqui: o celular e o desktop avaliam o
  // mesmo almoço ao mesmo tempo.

  // Editar não pontua de novo: sem aviso novo.
  await page.getByRole('button', { name: 'Fechar o aviso de pontos' }).click()
  await expect(page.getByText('+5 pontos')).toBeHidden()
  await avaliacoes.getByRole('button', { name: 'Editar' }).click()
  await avaliacoes.getByRole('radio', { name: '5 estrelas — Ótimo' }).click()
  await avaliacoes.getByRole('button', { name: 'Salvar alteração' }).click()
  await expect(avaliacoes).toContainText('Avaliação atualizada!')
  await expect(avaliacoes).toContainText('Sua nota: 5 estrelas')
  await expect(page.getByText(/\+\d+ pontos?/)).toBeHidden()
})
