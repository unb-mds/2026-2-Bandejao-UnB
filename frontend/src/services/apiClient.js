/**
 * apiClient — único ponto do frontend que fala com o backend (C4 nível 3b).
 *
 * - Conhece a URL base da API (VITE_API_URL, padrão "/api").
 * - Injeta o token da sessão quando há usuário autenticado.
 * - Converte qualquer falha em `ApiError`, com mensagem pronta para a tela.
 *
 * Enquanto a API Django não expõe todos os endpoints, o cliente usa um
 * backend simulado em memória (src/services/mock). Para apontar para a API
 * real, defina VITE_USE_MOCK=false no arquivo .env.local.
 */
import { tratarRequisicaoSimulada } from './mock/servidor'

const URL_BASE = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '')
export const USANDO_SIMULACAO = import.meta.env.VITE_USE_MOCK !== 'false'

const MENSAGEM_SEM_CONEXAO = 'Não foi possível conectar ao servidor. Verifique sua internet.'
const MENSAGEM_GENERICA = 'Algo deu errado. Tente novamente em instantes.'

export class ApiError extends Error {
  /**
   * @param {number} status código HTTP (0 = sem conexão)
   * @param {string} mensagem texto amigável para exibir ao usuário
   * @param {object} [dados] corpo da resposta de erro (ex.: { codigo })
   */
  constructor(status, mensagem, dados = {}) {
    super(mensagem)
    this.name = 'ApiError'
    this.status = status
    this.codigo = dados.codigo ?? null
    this.dados = dados
  }
}

let tokenSessao = null

/** Chamado pelo authStore ao entrar e ao sair. */
export function definirToken(token) {
  tokenSessao = token
}

async function requisitar(metodo, caminho, corpo) {
  const resposta = USANDO_SIMULACAO
    ? await tratarRequisicaoSimulada({ metodo, caminho, corpo, token: tokenSessao })
    : await requisitarHttp(metodo, caminho, corpo)

  if (resposta.status >= 200 && resposta.status < 300) return resposta.dados

  const dados = resposta.dados ?? {}
  throw new ApiError(resposta.status, dados.detail ?? MENSAGEM_GENERICA, dados)
}

async function requisitarHttp(metodo, caminho, corpo) {
  const opcoes = { method: metodo, headers: { Accept: 'application/json' } }
  if (corpo !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json'
    opcoes.body = JSON.stringify(corpo)
  }
  if (tokenSessao) opcoes.headers.Authorization = `Token ${tokenSessao}`

  let resposta
  try {
    resposta = await fetch(`${URL_BASE}${caminho}`, opcoes)
  } catch {
    throw new ApiError(0, MENSAGEM_SEM_CONEXAO)
  }
  return { status: resposta.status, dados: await lerJson(resposta) }
}

async function lerJson(resposta) {
  const texto = await resposta.text()
  try {
    return texto ? JSON.parse(texto) : null
  } catch {
    return null
  }
}

export const apiClient = {
  get: (caminho) => requisitar('GET', caminho),
  post: (caminho, corpo = {}) => requisitar('POST', caminho, corpo),
}
