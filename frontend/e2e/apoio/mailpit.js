import { expect } from '@playwright/test'

/** API do Mailpit, o SMTP de teste do e2e/docker-compose.yml. */
export const MAILPIT = process.env.E2E_MAILPIT_URL ?? 'http://localhost:8025'

/**
 * Link de confirmação do e-mail mandado para `email` (RF02). Espera o e-mail
 * chegar: o backend envia na mesma requisição do cadastro, mas o Mailpit pode
 * levar um instante para indexar. Um erro do Mailpit aparece com o status
 * HTTP, e não como um TypeError ao ler a resposta.
 */
export async function linkDeConfirmacao(request, email) {
  let id
  await expect
    .poll(
      async () => {
        const resposta = await request.get(`${MAILPIT}/api/v1/search`, {
          params: { query: `to:"${email}"` },
        })
        await expect(resposta, 'busca no Mailpit').toBeOK()
        const { messages } = await resposta.json()
        id = messages[0]?.ID
        return id
      },
      { message: `e-mail de confirmação para ${email}`, timeout: 15_000 },
    )
    .toBeTruthy()

  const resposta = await request.get(`${MAILPIT}/api/v1/message/${id}`)
  await expect(resposta, 'mensagem no Mailpit').toBeOK()
  const { Text: texto } = await resposta.json()
  const link = texto.match(/https?:\/\/\S+\/confirmar-email\?token=[\w-]+/)?.[0]
  expect(link, 'link de confirmação no texto do e-mail').toBeTruthy()
  return link
}
