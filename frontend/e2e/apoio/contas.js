import { expect } from '@playwright/test'

/** Senha das contas da fixture e2e/dados/contas.json. */
export const SENHA = 'senha-e2e-2026'

// Uma conta por fluxo e por projeto: os dois projetos rodam ao mesmo tempo, e
// cada conta só faz um check-in por refeição.
const CONTAS = {
  checkin: { celular: '260000101', desktop: '260000102' },
  avaliacao: { celular: '260000103', desktop: '260000104' },
  progresso: { celular: '260000105', desktop: '260000106' },
  longe: { celular: '260000107', desktop: '260000108' },
}
const APELIDOS = {
  checkin: { celular: 'e2e_checkin_cel', desktop: 'e2e_checkin_desk' },
  avaliacao: { celular: 'e2e_aval_cel', desktop: 'e2e_aval_desk' },
  progresso: { celular: 'e2e_prog_cel', desktop: 'e2e_prog_desk' },
  longe: { celular: 'e2e_longe_cel', desktop: 'e2e_longe_desk' },
}

/** Conta da fixture para o fluxo, no projeto (celular ou desktop) do teste. */
export function contaDoFluxo(fluxo, testInfo) {
  const projeto = testInfo.project.name
  const matricula = CONTAS[fluxo][projeto]
  return { email: `${matricula}@aluno.unb.br`, senha: SENHA, apelido: APELIDOS[fluxo][projeto] }
}

/** Entra pela tela de login, voltando para `voltar` depois. */
export async function entrar(page, { email, senha }, voltar = '/') {
  await page.goto(`/login?voltar=${encodeURIComponent(voltar)}`)
  await page.getByRole('textbox', { name: 'E-mail institucional' }).fill(email)
  await page.getByRole('textbox', { name: 'Senha' }).fill(senha)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).not.toHaveURL(/\/login/)
}
