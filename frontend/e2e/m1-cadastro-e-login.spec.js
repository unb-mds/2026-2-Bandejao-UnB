import { randomInt } from 'node:crypto'
import { test, expect } from './apoio/teste'
import { linkDeConfirmacao } from './apoio/mailpit'

/**
 * M1: cadastro, confirmação do e-mail, login e logout (RF01, RF02, RF03,
 * fluxo 4b).
 * Conta nova a cada execução, com o e-mail lido do Mailpit.
 */
test('cadastro de aluno, confirmação pelo link do e-mail, login e logout', async ({
  page,
  request,
}) => {
  // Matrícula aleatória de 7 dígitos depois do ano de ingresso (24): o banco
  // é limpo a cada rodada, e o sorteio só evita a colisão entre os projetos.
  const sufixo = String(randomInt(10_000_000)).padStart(7, '0')
  const matricula = `24${sufixo}`
  const apelido = `e2e_m1_${sufixo}`
  const email = `${matricula}@aluno.unb.br`
  const senha = 'senha-forte-e2e'

  await page.goto('/cadastro')
  await page.getByRole('radio', { name: 'Aluno' }).click()
  await page.getByRole('textbox', { name: 'Apelido (nick)' }).fill(apelido)
  await page.getByRole('textbox', { name: 'E-mail institucional' }).fill(email)
  await page.getByRole('textbox', { name: 'Senha' }).fill(senha)
  // A caixa de verdade fica escondida; a pessoa clica no texto do aceite.
  await page.getByText(/Meus dados serão usados para login/).click()
  await expect(page.getByRole('checkbox', { name: /Li e aceito/ })).toBeChecked()
  await page.getByRole('button', { name: 'Criar conta' }).click()

  await expect(page).toHaveURL(/\/confirmar-email/)
  await expect(page.getByText(email)).toBeVisible()

  // Antes de confirmar, o login é recusado (RF02).
  await page.goto('/login')
  await page.getByRole('textbox', { name: 'E-mail institucional' }).fill(email)
  await page.getByRole('textbox', { name: 'Senha' }).fill(senha)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('alert')).toContainText(/confirm/i)
  await expect(page).toHaveURL(/\/login/)

  await page.goto(await linkDeConfirmacao(request, email))
  await expect(page.getByText('Conta confirmada!')).toBeVisible()

  await page.getByRole('link', { name: 'Entrar' }).click()
  await page.getByRole('textbox', { name: 'E-mail institucional' }).fill(email)
  await page.getByRole('textbox', { name: 'Senha' }).fill(senha)
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(page).not.toHaveURL(/\/login/)
  await page.goto('/progresso')
  await expect(page.getByText(apelido)).toBeVisible()

  // Logout (RF03.3): volta às boas-vindas, e a sessão acabou no servidor.
  await page.getByRole('button', { name: 'Sair da conta' }).click()
  await expect(page).toHaveURL(/\/boas-vindas/)
  await expect(page.getByRole('link', { name: 'Entrar na conta' })).toBeVisible()
  await page.goto('/progresso')
  await expect(page.getByText('Entre para ver seu progresso')).toBeVisible()
  await expect(page.getByText(apelido)).toBeHidden()
})
