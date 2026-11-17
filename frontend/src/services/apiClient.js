/**
 * apiClient — único ponto do frontend que fala com o backend (C4 nível 3b,
 * ADR 0007).
 *
 * - Conhece a URL base da API (VITE_API_URL, padrão "/api").
 * - Sessão por cookie HttpOnly: o `fetch` vai com `credentials: 'same-origin'`
 *   e nenhum token passa pelo JavaScript.
 * - Nas escritas (POST, PUT, PATCH, DELETE) manda o cabeçalho `X-CSRFToken`,
 *   lido do cookie `csrftoken` que o Django grava. O backend cobra o CSRF até
 *   de quem não tem sessão (cadastro, login): se o cookie ainda não existe, o
 *   apiClient chama `GET /api/csrf/` antes da escrita (#112). O cookie é lido
 *   a cada escrita, porque o login troca o token.
 * - Um 401 avisa quem se registrou em `definirAoPerderSessao` (o authStore,
 *   que se limpa). Um 403 `csrf_invalido` não desloga ninguém.
 * - Converte qualquer falha em `ApiError`, com `status`, `codigo` e a
 *   `mensagem` do contrato (`{ codigo, mensagem }`). Sem `mensagem`, usa uma
 *   em português pelo status (nunca o `detail` em inglês do DRF). As telas
 *   mostram erros com `mensagemDeErro`.
 *
 * O servidor simulado (src/services/mock) só existe em desenvolvimento e nos
 * testes: no build de produção `import.meta.env.DEV` é `false` e o Vite
 * remove o import dele. Para usar a API real em desenvolvimento, defina
 * VITE_USE_MOCK=false no .env.local (o Vite encaminha /api ao Django).
 */

const URL_BASE = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '')
export const USANDO_SIMULACAO = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK !== 'false'

const METODOS_DE_ESCRITA = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const MENSAGEM_GENERICA = 'Algo deu errado. Tente novamente em instantes.'

/**
 * Mensagem para o usuário quando a resposta não traz `mensagem` (o backend
 * sempre traz desde o #132; sobram erros de fora da API e o `detail` do DRF).
 * O `detail` em si fica só em `ApiError.dados`.
 */
const MENSAGENS_POR_STATUS = {
  0: 'Não foi possível conectar ao servidor. Verifique sua internet.',
  401: 'É preciso entrar na conta para continuar.',
  403: 'Você não tem permissão para fazer isso.',
  404: 'Não encontramos o que você pediu.',
  429: 'Muitos pedidos seguidos. Tente de novo mais tarde.',
}

function mensagemPorStatus(status) {
  if (MENSAGENS_POR_STATUS[status]) return MENSAGENS_POR_STATUS[status]
  if (status >= 500) return 'O servidor está com problemas. Tente de novo em instantes.'
  return MENSAGEM_GENERICA
}

export class ApiError extends Error {
  /**
   * @param {number} status código HTTP (0 = sem conexão)
   * @param {object} [dados] corpo da resposta de erro (`{ codigo, mensagem, ... }`)
   */
  constructor(status, dados = {}) {
    super(dados.mensagem ?? mensagemPorStatus(status))
    this.name = 'ApiError'
    this.status = status
    this.codigo = dados.codigo ?? null
    this.dados = dados
  }
}

/**
 * O que as telas mostram num `catch`. Erro da API: a mensagem dele. Qualquer
 * outro (ex.: um `TypeError` de programação) vira a mensagem genérica, em vez
 * de texto em inglês na tela, e vai para o console.
 */
export function mensagemDeErro(falha) {
  if (falha instanceof ApiError) return falha.message
  console.error(falha)
  return MENSAGEM_GENERICA
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

/** Pedido de `GET /api/csrf/` em andamento: escritas simultâneas esperam o mesmo. */
let pedidoCsrf = null

async function buscarCookieCsrf(transporte) {
  const resposta = await transporte({
    metodo: 'GET',
    caminho: '/csrf/',
    cabecalhos: { Accept: 'application/json' },
  })
  if (resposta.status < 200 || resposta.status >= 300) {
    throw new ApiError(resposta.status, resposta.dados ?? {})
  }
  if (!lerCookie('csrftoken')) {
    throw new ApiError(resposta.status, {
      codigo: 'csrf_indisponivel',
      mensagem: 'Não foi possível preparar o envio. Recarregue a página e tente de novo.',
    })
  }
}

async function garantirCookieCsrf(transporte) {
  if (lerCookie('csrftoken')) return
  pedidoCsrf ??= buscarCookieCsrf(transporte).finally(() => {
    pedidoCsrf = null
  })
  await pedidoCsrf
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

const semConexao = () => new ApiError(0, { codigo: 'sem_conexao', mensagem: mensagemPorStatus(0) })

async function requisitarHttp({ metodo, caminho, corpo, cabecalhos }) {
  const opcoes = { method: metodo, headers: cabecalhos, credentials: 'same-origin' }
  if (corpo !== undefined) opcoes.body = JSON.stringify(corpo)

  let resposta
  let texto
  try {
    resposta = await fetch(`${URL_BASE}${caminho}`, opcoes)
    // Dentro do mesmo try: a conexão também pode cair no meio do corpo.
    texto = await resposta.text()
  } catch {
    throw semConexao()
  }

  if (!texto) return { status: resposta.status, dados: null }
  try {
    return { status: resposta.status, dados: JSON.parse(texto) }
  } catch {
    // Sucesso com corpo que não é JSON (ex.: o index.html do PWA quando a URL
    // da API está errada) não pode passar como "deu certo".
    if (resposta.ok) {
      throw new ApiError(resposta.status, {
        codigo: 'resposta_invalida',
        mensagem: MENSAGEM_GENERICA,
      })
    }
    return { status: resposta.status, dados: null }
  }
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

/**
 * @param {{ simulado?: boolean }} [opcoes] `simulado: false` força o HTTP
 *   (usado nos testes do próprio apiClient).
 */
export function criarApiClient({ simulado = USANDO_SIMULACAO } = {}) {
  const transporte = simulado ? requisitarSimulado : requisitarHttp

  async function requisitar(metodo, caminho, corpo) {
    if (METODOS_DE_ESCRITA.has(metodo)) await garantirCookieCsrf(transporte)
    const pedido = { metodo, caminho, corpo, cabecalhos: montarCabecalhos(metodo, corpo) }
    const resposta = await transporte(pedido)

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
