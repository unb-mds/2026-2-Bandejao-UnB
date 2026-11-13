import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, definirAoPerderSessao } from '@/services/apiClient'

/**
 * Sessão do usuário (RF01–RF04). Sem token (ADR 0007): a sessão fica no
 * cookie HttpOnly e a store guarda só o que `/api/sessao/` devolve —
 * apelido, tipo e avisoPrivacidadePendente. Um 401 em qualquer rota limpa a
 * store (o apiClient avisa). Os corpos seguem o contrato OpenAPI v1 (BE-03).
 */
export const useAuthStore = defineStore('auth', () => {
  /** @type {import('vue').Ref<{ apelido: string, tipo: string, avisoPrivacidadePendente: boolean } | null>} */
  const usuario = ref(null)

  const estaAutenticado = computed(() => Boolean(usuario.value))
  const apelido = computed(() => usuario.value?.apelido ?? 'Visitante')

  function limpar() {
    usuario.value = null
  }
  definirAoPerderSessao(limpar)

  /** POST /api/sessao/ — matrícula (9 dígitos) ou SIAPE (7) no mesmo campo. */
  async function entrar(matriculaSiape, senha) {
    usuario.value = await apiClient.post('/sessao/', {
      matriculaSiape: matriculaSiape.trim(),
      senha,
    })
  }

  /** DELETE /api/sessao/ */
  async function sair() {
    try {
      await apiClient.delete('/sessao/')
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
   */
  function reenviarConfirmacao({ matriculaSiape, token } = {}) {
    const corpo = matriculaSiape ? { matriculaSiape: matriculaSiape.trim() } : { token }
    return apiClient.post('/reenviar-confirmacao/', corpo)
  }

  function solicitarRecuperacao(email) {
    return apiClient.post('/recuperar-senha/', { email: email.trim() })
  }

  function redefinirSenha(tokenRedefinicao, senha) {
    return apiClient.post('/redefinir-senha/', { token: tokenRedefinicao, senha })
  }

  return {
    usuario,
    estaAutenticado,
    apelido,
    limpar,
    entrar,
    sair,
    cadastrar,
    confirmarEmail,
    reenviarConfirmacao,
    solicitarRecuperacao,
    redefinirSenha,
  }
})
