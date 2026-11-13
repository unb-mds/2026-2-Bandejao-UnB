/**
 * apiClient — único ponto do frontend que fala com o backend (C4 nível 3b,
 * ADR 0007).
 *
 * - Conhece a URL base da API (VITE_API_URL, padrão "/api").
 * - Sessão por cookie HttpOnly: o `fetch` vai com `credentials: 'same-origin'`
 *   e nenhum token passa pelo JavaScript.
 * - Nas escritas (POST, PUT, PATCH, DELETE) manda o cabeçalho `X-CSRFToken`,
 *   lido do cookie `csrftoken` que o Django grava.
 * - Um 401 avisa quem se registrou em `definirAoPerderSessao` (o authStore,
 *   que se limpa). Um 403 de CSRF não desloga ninguém.
 * - Converte qualquer falha em `ApiError`, com `status`, `codigo` e a
 *   `mensagem` do contrato (`{ codigo, mensagem }`).
 *
 * O servidor simulado (src/services/mock) só existe em desenvolvimento e nos
 * testes: no build de produção `import.meta.env.DEV` é `false` e o Vite
 * remove o import dele. Para usar a API real em desenvolvimento, defina
 * VITE_USE_MOCK=false no .env.local (o Vite encaminha /api ao Django).
 */

const URL_BASE = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '')
export const USANDO_SIMULACAO = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK !== 'false'

const METODOS_DE_ESCRITA = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const MENSAGEM_SEM_CONEXAO = 'Não foi possível conectar ao servidor. Verifique sua internet.'
const MENSAGEM_GENERICA = 'Algo deu errado. Tente novamente em instantes.'

export class ApiError extends Error {
  /**
   * @param {number} status código HTTP (0 = sem conexão)
   * @param {object} [dados] corpo da resposta de erro (`{ codigo, mensagem, ... }`)
   */
  constructor(status, dados = {}) {
    // `detail` cobre os erros que o DRF ainda devolve no formato dele (BE-05).
    super(dados.mensagem ?? dados.detail ?? MENSAGEM_GENERICA)
    this.name = 'ApiError'
    this.status = status
    this.codigo = dados.codigo ?? null
    this.dados = dados
  }
}

let aoPerderSessao = null

/** O authStore registra aqui a função que o limpa quando chega um 401. */
export function definirAoPerderSessao(funcao) {
  aoPerderSessao = funcao
}

function lerCookie(nome) {
  if (typeof document === 'undefined') return null
  const par = document.cookie.split('; ').find((item) => item.startsWith(`${nome}=`))
  const valor = par ? decodeURIComponent(par.slice(nome.length + 1)) : ''
  return valor || null
}

function montarCabecalhos(metodo, corpo) {
  const cabecalhos = { Accept: 'application/json' }
  if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'
  if (METODOS_DE_ESCRITA.has(metodo)) {
    const csrf = lerCookie('csrftoken')
    if (csrf) cabecalhos['X-CSRFToken'] = csrf
  }
  return cabecalhos
}

async function requisitarHttp({ metodo, caminho, corpo, cabecalhos }) {
  const opcoes = { method: metodo, headers: cabecalhos, credentials: 'same-origin' }
  if (corpo !== undefined) opcoes.body = JSON.stringify(corpo)

  let resposta
  try {
    resposta = await fetch(`${URL_BASE}${caminho}`, opcoes)
  } catch {
    throw new ApiError(0, { codigo: 'sem_conexao', mensagem: MENSAGEM_SEM_CONEXAO })
  }
  return { status: resposta.status, dados: await lerJson(resposta) }
}

async function requisitarSimulado(pedido) {
  // `import.meta.env.DEV` em linha (e não só USANDO_SIMULACAO) para o Vite
  // cortar este import do build de produção.
  if (import.meta.env.DEV) {
    const { tratarRequisicaoSimulada } = await import('./mock/servidor')
    return tratarRequisicaoSimulada(pedido)
  }
  throw new Error('Servidor simulado indisponível em produção.')
}

async function lerJson(resposta) {
  const texto = await resposta.text()
  try {
    return texto ? JSON.parse(texto) : null
  } catch {
    return null
  }
}

/**
 * @param {{ simulado?: boolean }} [opcoes] `simulado: false` força o HTTP
 *   (usado nos testes do próprio apiClient).
 */
export function criarApiClient({ simulado = USANDO_SIMULACAO } = {}) {
  async function requisitar(metodo, caminho, corpo) {
    const pedido = { metodo, caminho, corpo, cabecalhos: montarCabecalhos(metodo, corpo) }
    const resposta = simulado ? await requisitarSimulado(pedido) : await requisitarHttp(pedido)

    if (resposta.status >= 200 && resposta.status < 300) return resposta.dados ?? null

    if (resposta.status === 401) aoPerderSessao?.()
    throw new ApiError(resposta.status, resposta.dados ?? {})
  }

  return {
    get: (caminho) => requisitar('GET', caminho),
    post: (caminho, corpo) => requisitar('POST', caminho, corpo),
    put: (caminho, corpo) => requisitar('PUT', caminho, corpo),
    patch: (caminho, corpo) => requisitar('PATCH', caminho, corpo),
    delete: (caminho) => requisitar('DELETE', caminho),
  }
}

export const apiClient = criarApiClient()
