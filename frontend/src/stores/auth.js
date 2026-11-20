import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, definirAoPerderSessao } from '@/services/apiClient'

/**
 * Sessão do usuário (RF01–RF04). Sem token (ADR 0007): a sessão fica no
 * cookie HttpOnly e a store guarda só o que `/api/sessao/` devolve —
 * apelido, tipo e avisoPrivacidadePendente. Um 401 em qualquer rota limpa a
 * store (o apiClient avisa). Os corpos seguem o contrato OpenAPI v1 (BE-03).
 */
// O backend responde o reenvio com 200 sem corpo, exista ou não a conta (RF02.2).
// Quanto a primeira tela espera pelo `GET /sessao/` antes de seguir como visitante.
const LIMITE_SESSAO_MS = 3000

const MENSAGEM_REENVIO =
  'Se houver um cadastro pendente, enviamos um novo link de confirmação para o e-mail institucional.'

export const useAuthStore = defineStore('auth', () => {
  /** @type {import('vue').Ref<{ apelido: string, tipo: string, avisoPrivacidadePendente: boolean } | null>} */
  const usuario = ref(null)

  /** Já perguntou ao servidor se há sessão (`carregarSessao`), deu certo ou não. */
  const sessaoCarregada = ref(false)
  let carregandoSessao = null
  // Muda a cada login ou logout: uma resposta atrasada do boot não desfaz o que veio depois.
  let geracao = 0

  const estaAutenticado = computed(() => Boolean(usuario.value))
  const apelido = computed(() => usuario.value?.apelido ?? 'Visitante')

  function limpar() {
    geracao++
    usuario.value = null
  }
  definirAoPerderSessao(limpar)

  /**
   * GET /api/sessao/ ao abrir o app: o cookie de sessão sobrevive ao F5, a
   * store não (ADR 0007). Nunca rejeita: sem sessão (401) ou sem conexão, o
   * app abre como visitante. Chamadas ao mesmo tempo esperam o mesmo pedido.
   *
   * Espera no máximo 3 s (rede lenta, como o Wi-Fi do RU): depois disso o app
   * segue como visitante, e se a resposta chegar mais tarde o apelido aparece.
   * Se o pedido falhar (sem conexão, 500), quem tinha sessão aparece como
   * visitante até recarregar a página: o guarda não tenta de novo.
   */
  function carregarSessao() {
    if (carregandoSessao) return carregandoSessao
    const geracaoDoPedido = geracao
    const pedido = apiClient
      .get('/sessao/', { avisarSessaoPerdida: false })
      .then((sessao) => {
        if (geracao === geracaoDoPedido) usuario.value = sessao
      })
      .catch(() => {
        if (geracao === geracaoDoPedido) usuario.value = null
      })
    let temporizador
    const limite = new Promise((resolver) => {
      temporizador = setTimeout(resolver, LIMITE_SESSAO_MS)
    })
    carregandoSessao = Promise.race([pedido, limite]).finally(() => {
      clearTimeout(temporizador)
      sessaoCarregada.value = true
      carregandoSessao = null
    })
    return carregandoSessao
  }

  /** POST /api/sessao/ — matrícula (9 dígitos) ou SIAPE (7) no mesmo campo. */
  async function entrar(matriculaSiape, senha) {
    geracao++
    usuario.value = await apiClient.post('/sessao/', {
      matriculaSiape: matriculaSiape.trim(),
      senha,
    })
  }

  /**
   * DELETE /api/sessao/. Um 401 quer dizer que a sessão já tinha acabado no
   * servidor: para quem clicou em "Sair", deu certo do mesmo jeito.
   */
  async function sair() {
    try {
      await apiClient.delete('/sessao/')
    } catch (falha) {
      if (falha.status !== 401) throw falha
    } finally {
      limpar()
    }
  }

  /**
   * POST /api/cadastro/ com `{ tipoUsuario, emailInstitucional, senha,
   * apelido?, matriculaSiape?, aceitePrivacidade }`.
   * @returns {Promise<{ emailInstitucional: string, status: 'pendente', linkSimulado?: string }>}
   */
  function cadastrar(dados) {
    return apiClient.post('/cadastro/', dados)
  }

  /** POST /api/confirmar-email/{token}/ */
  function confirmarEmail(tokenConfirmacao) {
    return apiClient.post(`/confirmar-email/${encodeURIComponent(tokenConfirmacao)}/`)
  }

  /**
   * POST /api/reenviar-confirmacao/ com um dos dois campos:
   * `{ matriculaSiape }` (tela de login) ou `{ token }` (link expirado).
   * @returns {Promise<{ mensagem: string, linkSimulado?: string }>}
   */
  async function reenviarConfirmacao({ matriculaSiape, token } = {}) {
    const corpo = matriculaSiape ? { matriculaSiape: matriculaSiape.trim() } : { token }
    const resposta = await apiClient.post('/reenviar-confirmacao/', corpo)
    return { mensagem: MENSAGEM_REENVIO, linkSimulado: resposta?.linkSimulado }
  }

  function solicitarRecuperacao(email) {
    return apiClient.post('/recuperar-senha/', { email: email.trim() })
  }

  function redefinirSenha(tokenRedefinicao, senha) {
    return apiClient.post('/redefinir-senha/', { token: tokenRedefinicao, senha })
  }

  return {
    usuario,
    sessaoCarregada,
    estaAutenticado,
    apelido,
    limpar,
    carregarSessao,
    entrar,
    sair,
    cadastrar,
    confirmarEmail,
    reenviarConfirmacao,
    solicitarRecuperacao,
    redefinirSenha,
  }
})
