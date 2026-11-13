import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, criarApiClient, definirAoPerderSessao } from './apiClient'

/**
 * Testes do apiClient falando HTTP de verdade (com o `fetch` trocado por um
 * dublê). O servidor simulado fica de fora: aqui interessa o que sai do
 * navegador (ADR 0007, Plano de Testes 3.6, FE-01).
 */
const cliente = criarApiClient({ simulado: false })

function respostaJson(status, corpo) {
  return Promise.resolve(
    new Response(corpo === undefined ? null : JSON.stringify(corpo), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

let fetchFalso

function apagarCookieCsrf() {
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
}

function ultimaChamada() {
  const [url, opcoes] = fetchFalso.mock.calls.at(-1)
  return { url, opcoes, cabecalhos: opcoes.headers }
}

beforeEach(() => {
  fetchFalso = vi.fn(() => respostaJson(200, { ok: true }))
  vi.stubGlobal('fetch', fetchFalso)
  document.cookie = 'csrftoken=token-csrf-123; path=/'
})

afterEach(() => {
  vi.unstubAllGlobals()
  apagarCookieCsrf()
  definirAoPerderSessao(null)
})

describe('cookie de sessão (ADR 0007)', () => {
  it('toda requisição manda o cookie com credentials same-origin', async () => {
    await cliente.get('/sessao/')
    expect(ultimaChamada().opcoes.credentials).toBe('same-origin')

    await cliente.post('/sessao/', { matriculaSiape: '231034567', senha: 'x' })
    expect(ultimaChamada().opcoes.credentials).toBe('same-origin')
  })

  it('não injeta token nenhum: a sessão está só no cookie HttpOnly', async () => {
    await cliente.post('/avaliacoes/', { nota: 5 })
    expect(ultimaChamada().cabecalhos).not.toHaveProperty('Authorization')
  })

  it('usa a URL base /api', async () => {
    await cliente.get('/sessao/')
    expect(ultimaChamada().url).toBe('/api/sessao/')
  })
})

describe('CSRF nas escritas', () => {
  it.each([
    ['post', 'POST'],
    ['put', 'PUT'],
    ['patch', 'PATCH'],
    ['delete', 'DELETE'],
  ])('%s manda X-CSRFToken com o valor do cookie csrftoken', async (funcao, metodo) => {
    await cliente[funcao]('/gamificacao/adesao/')
    const { opcoes, cabecalhos } = ultimaChamada()
    expect(opcoes.method).toBe(metodo)
    expect(cabecalhos['X-CSRFToken']).toBe('token-csrf-123')
  })

  it('GET não manda X-CSRFToken (leitura não altera estado)', async () => {
    await cliente.get('/sessao/')
    expect(ultimaChamada().cabecalhos).not.toHaveProperty('X-CSRFToken')
  })

  it('lê o cookie na hora da requisição (o Django troca o token no login)', async () => {
    document.cookie = 'csrftoken=token-novo; path=/'
    await cliente.delete('/sessao/')
    expect(ultimaChamada().cabecalhos['X-CSRFToken']).toBe('token-novo')
  })

  it('sem cookie csrftoken, não inventa cabeçalho', async () => {
    apagarCookieCsrf()
    await cliente.post('/cadastro/', {})
    expect(ultimaChamada().cabecalhos).not.toHaveProperty('X-CSRFToken')
  })
})

describe('erro com codigo', () => {
  it('converte o corpo { codigo, mensagem } do contrato em ApiError', async () => {
    fetchFalso.mockReturnValueOnce(
      respostaJson(403, { codigo: 'conta_nao_confirmada', mensagem: 'Confirme seu e-mail.' }),
    )

    const falha = await cliente.post('/sessao/', {}).catch((e) => e)

    expect(falha).toBeInstanceOf(ApiError)
    expect(falha.status).toBe(403)
    expect(falha.codigo).toBe('conta_nao_confirmada')
    expect(falha.message).toBe('Confirme seu e-mail.')
  })

  it('guarda o corpo inteiro para campos extras (ex.: apelidoSugerido no 409)', async () => {
    fetchFalso.mockReturnValueOnce(
      respostaJson(409, {
        codigo: 'apelido_indisponivel',
        mensagem: 'Escolha outro apelido.',
        apelidoSugerido: 'maria1',
      }),
    )
    const falha = await cliente.post('/cadastro/', {}).catch((e) => e)
    expect(falha.dados.apelidoSugerido).toBe('maria1')
  })

  it('erro sem corpo JSON vira mensagem genérica, sem codigo', async () => {
    fetchFalso.mockReturnValueOnce(Promise.resolve(new Response('<html>', { status: 502 })))
    const falha = await cliente.get('/sessao/').catch((e) => e)
    expect(falha.status).toBe(502)
    expect(falha.codigo).toBeNull()
    expect(falha.message).toMatch(/algo deu errado/i)
  })

  it('sem conexão vira status 0 com codigo sem_conexao', async () => {
    fetchFalso.mockReturnValueOnce(Promise.reject(new TypeError('Failed to fetch')))
    const falha = await cliente.get('/sessao/').catch((e) => e)
    expect(falha.status).toBe(0)
    expect(falha.codigo).toBe('sem_conexao')
  })

  it('204 sem corpo devolve null', async () => {
    fetchFalso.mockReturnValueOnce(Promise.resolve(new Response(null, { status: 204 })))
    expect(await cliente.delete('/sessao/')).toBeNull()
  })
})

describe('401 avisa que a sessão acabou', () => {
  it('chama quem foi registrado (o authStore se limpa)', async () => {
    const aoPerder = vi.fn()
    definirAoPerderSessao(aoPerder)
    fetchFalso.mockReturnValueOnce(
      respostaJson(401, { codigo: 'nao_autenticado', mensagem: 'Entre na conta.' }),
    )

    const falha = await cliente.get('/sessao/').catch((e) => e)

    expect(aoPerder).toHaveBeenCalledTimes(1)
    expect(falha.codigo).toBe('nao_autenticado')
  })

  it('403 de CSRF não desloga ninguém', async () => {
    const aoPerder = vi.fn()
    definirAoPerderSessao(aoPerder)
    fetchFalso.mockReturnValueOnce(
      respostaJson(403, { detail: 'CSRF Failed: CSRF token missing.' }),
    )

    const falha = await cliente.post('/avaliacoes/', {}).catch((e) => e)

    expect(aoPerder).not.toHaveBeenCalled()
    expect(falha.status).toBe(403)
  })
})
