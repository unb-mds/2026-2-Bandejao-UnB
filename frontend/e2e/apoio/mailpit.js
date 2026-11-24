import { expect } from '@playwright/test'

/** API do Mailpit, o SMTP de teste do e2e/docker-compose.yml. */
const MAILPIT = process.env.E2E_MAILPIT_URL ?? 'http://localhost:8025'

/**
 * Link de confirmação do e-mail mandado para `email` (RF02). Espera o e-mail
 * chegar: o backend envia na mesma requisição do cadastro, mas o Mailpit pode
 * levar um instante para indexar.
 */
export async function linkDeConfirmacao(request, email) {
  let id
  await expect
    .poll(
      async () => {
        const resposta = await request.get(`${MAILPIT}/api/v1/search`, {
          params: { query: `to:"${email}"` },
        })
        const { messages } = await resposta.json()
        id = messages[0]?.ID
        return id
      },
      { message: `e-mail de confirmação para ${email}`, timeout: 15_000 },
    )
    .toBeTruthy()

  const mensagem = await (await request.get(`${MAILPIT}/api/v1/message/${id}`)).json()
  const link = mensagem.Text.match(/https?:\/\/\S+\/confirmar-email\?token=[\w-]+/)?.[0]
  expect(link, 'link de confirmação no texto do e-mail').toBeTruthy()
  return link
}
