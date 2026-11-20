import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, criarApiClient, definirAoPerderSessao, mensagemDeErro } from './apiClient'

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

    await cliente.post('/sessao/', { emailInstitucional: '231034567@aluno.unb.br', senha: 'x' })
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

  it('sem cookie csrftoken, pede GET /api/csrf/ antes da escrita (cadastro, login)', async () => {
    apagarCookieCsrf()
    fetchFalso.mockImplementationOnce(() => {
      document.cookie = 'csrftoken=vindo-do-servidor; path=/'
      return Promise.resolve(new Response(null, { status: 204 }))
    })

    await cliente.post('/cadastro/', {})

    const [urlCsrf, opcoesCsrf] = fetchFalso.mock.calls[0]
    expect(urlCsrf).toBe('/api/csrf/')
    expect(opcoesCsrf.method).toBe('GET')
    expect(ultimaChamada().url).toBe('/api/cadastro/')
    expect(ultimaChamada().cabecalhos['X-CSRFToken']).toBe('vindo-do-servidor')
  })

  it('escritas ao mesmo tempo, sem cookie, pedem o /api/csrf/ uma vez só', async () => {
    apagarCookieCsrf()
    // O cookie só chega quando a resposta do /csrf/ volta, depois das duas
    // escritas já terem começado: sem o pedido compartilhado, cada uma
    // chamaria o /csrf/ por conta própria.
    let responderCsrf
    fetchFalso.mockImplementationOnce(
      () =>
        new Promise((resolver) => {
          responderCsrf = () => {
            document.cookie = 'csrftoken=vindo-do-servidor; path=/'
            resolver(new Response(null, { status: 204 }))
          }
        }),
    )

    const escritas = Promise.all([cliente.post('/cadastro/', {}), cliente.post('/sessao/', {})])
    await new Promise((resolver) => setTimeout(resolver, 0))
    responderCsrf()
    await escritas

    const urls = fetchFalso.mock.calls.map(([url]) => url)
    expect(urls.filter((url) => url === '/api/csrf/')).toHaveLength(1)
    const escritasFeitas = fetchFalso.mock.calls.filter(([url]) => url !== '/api/csrf/')
    expect(escritasFeitas).toHaveLength(2)
    for (const [, opcoes] of escritasFeitas) {
      expect(opcoes.headers['X-CSRFToken']).toBe('vindo-do-servidor')
    }
  })

  it('se o GET /api/csrf/ falhar, a escrita não é enviada', async () => {
    apagarCookieCsrf()
    fetchFalso.mockReturnValueOnce(Promise.resolve(new Response('<html>', { status: 500 })))

    const falha = await cliente.post('/cadastro/', {}).catch((e) => e)

    expect(falha).toBeInstanceOf(ApiError)
    expect(falha.status).toBe(500)
    expect(fetchFalso.mock.calls.map(([url]) => url)).toEqual(['/api/csrf/'])
  })

  it('se o GET /api/csrf/ não gravar o cookie, a escrita não é enviada', async () => {
    apagarCookieCsrf()
    fetchFalso.mockReturnValueOnce(Promise.resolve(new Response(null, { status: 204 })))

    const falha = await cliente.post('/cadastro/', {}).catch((e) => e)

    expect(falha.codigo).toBe('csrf_indisponivel')
    expect(fetchFalso.mock.calls.map(([url]) => url)).toEqual(['/api/csrf/'])
  })

  it('com o cookie já gravado, não pede /api/csrf/ de novo', async () => {
    await cliente.post('/cadastro/', {})
    expect(fetchFalso.mock.calls.map(([url]) => url)).toEqual(['/api/cadastro/'])
  })

  it('GET não pede /api/csrf/', async () => {
    apagarCookieCsrf()
    await cliente.get('/sessao/')
    expect(fetchFalso.mock.calls.map(([url]) => url)).toEqual(['/api/sessao/'])
  })
})

describe('corpo da requisição e da resposta', () => {
  it('escrita com corpo manda JSON com Content-Type', async () => {
    await cliente.post('/sessao/', { emailInstitucional: '231034567@aluno.unb.br', senha: 'x' })
    const { opcoes, cabecalhos } = ultimaChamada()
    expect(opcoes.body).toBe(
      JSON.stringify({ emailInstitucional: '231034567@aluno.unb.br', senha: 'x' }),
    )
    expect(cabecalhos['Content-Type']).toBe('application/json')
  })

  it('pedido sem corpo não manda body nem Content-Type', async () => {
    await cliente.get('/sessao/')
    const { opcoes, cabecalhos } = ultimaChamada()
    expect(opcoes).not.toHaveProperty('body')
    expect(cabecalhos).not.toHaveProperty('Content-Type')
  })

  it('2xx com corpo vazio devolve null (ex.: reenvio de confirmação)', async () => {
    fetchFalso.mockReturnValueOnce(Promise.resolve(new Response('', { status: 200 })))
    expect(await cliente.post('/reenviar-confirmacao/', { token: 'x' })).toBeNull()
  })

  it('2xx com corpo que não é JSON vira erro resposta_invalida (ex.: index.html)', async () => {
    fetchFalso.mockReturnValueOnce(
      Promise.resolve(new Response('<!doctype html><html></html>', { status: 200 })),
    )

    const falha = await cliente.post('/sessao/', {}).catch((e) => e)

    expect(falha).toBeInstanceOf(ApiError)
    expect(falha.codigo).toBe('resposta_invalida')
    expect(falha.status).toBe(200)
  })

  it('conexão cortada no meio do corpo vira sem_conexao', async () => {
    const resposta = new Response('{"apelido":', { status: 200 })
    resposta.text = () => Promise.reject(new TypeError('network error'))
    fetchFalso.mockReturnValueOnce(Promise.resolve(resposta))

    const falha = await cliente.get('/sessao/').catch((e) => e)

    expect(falha).toBeInstanceOf(ApiError)
    expect(falha.codigo).toBe('sem_conexao')
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

  it('erro sem corpo JSON (ex.: página do proxy) vira mensagem pelo status, sem codigo', async () => {
    fetchFalso.mockReturnValueOnce(Promise.resolve(new Response('<html>', { status: 502 })))
    const falha = await cliente.get('/sessao/').catch((e) => e)
    expect(falha.status).toBe(502)
    expect(falha.codigo).toBeNull()
    expect(falha.message).toBe('O servidor está com problemas. Tente de novo em instantes.')
  })

  it('erro só com `detail` (inglês do DRF) mostra mensagem em português pelo status', async () => {
    fetchFalso.mockReturnValueOnce(respostaJson(404, { detail: 'Not found.' }))

    const falha = await cliente.post('/recuperar-senha/', {}).catch((e) => e)

    expect(falha.message).toBe('Não encontramos o que você pediu.')
    expect(falha.codigo).toBeNull()
    expect(falha.dados.detail).toBe('Not found.')
  })

  it('429 sem mensagem pede para esperar', async () => {
    fetchFalso.mockReturnValueOnce(respostaJson(429, { detail: 'Request was throttled.' }))
    const falha = await cliente.post('/cadastro/', {}).catch((e) => e)
    expect(falha.message).toBe('Muitos pedidos seguidos. Tente de novo mais tarde.')
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

  it('com `avisarSessaoPerdida: false`, um 401 é só a resposta (a sessão do boot)', async () => {
    const aoPerder = vi.fn()
    definirAoPerderSessao(aoPerder)
    fetchFalso.mockReturnValueOnce(respostaJson(401, { codigo: 'nao_autenticado' }))

    const falha = await cliente.get('/sessao/', { avisarSessaoPerdida: false }).catch((e) => e)

    expect(falha.status).toBe(401)
    expect(aoPerder).not.toHaveBeenCalled()
  })

  it('403 de CSRF não desloga ninguém', async () => {
    const aoPerder = vi.fn()
    definirAoPerderSessao(aoPerder)
    fetchFalso.mockReturnValueOnce(
      respostaJson(403, {
        codigo: 'csrf_invalido',
        mensagem:
          'Não foi possível confirmar a origem do pedido. Recarregue a página e tente de novo.',
      }),
    )

    const falha = await cliente.post('/avaliacoes/', {}).catch((e) => e)

    expect(aoPerder).not.toHaveBeenCalled()
    expect(falha.status).toBe(403)
    expect(falha.codigo).toBe('csrf_invalido')
  })
})

describe('mensagemDeErro (o que as telas mostram)', () => {
  it('ApiError: a mensagem do servidor', () => {
    const falha = new ApiError(403, {
      codigo: 'conta_nao_confirmada',
      mensagem: 'Confirme seu e-mail.',
    })
    expect(mensagemDeErro(falha)).toBe('Confirme seu e-mail.')
  })

  it('erro de programação (TypeError): mensagem genérica e registro no console', () => {
    const console = vi.spyOn(globalThis.console, 'error').mockImplementation(() => {})
    const falha = new TypeError("Cannot read properties of null (reading 'mensagem')")

    expect(mensagemDeErro(falha)).toBe('Algo deu errado. Tente novamente em instantes.')
    expect(console).toHaveBeenCalledWith(falha)

    console.mockRestore()
  })
})
