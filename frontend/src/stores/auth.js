import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, definirToken } from '@/services/apiClient'

/**
 * Sessão do usuário (RF01–RF04). Fica só em memória, por decisão do C4
 * (nível 3b): recarregar a página encerra a sessão.
 */
export const useAuthStore = defineStore('auth', () => {
  const usuario = ref(null)
  const token = ref(null)

  const estaAutenticado = computed(() => Boolean(token.value))
  const apelido = computed(() => usuario.value?.apelido ?? 'Visitante')

  async function entrar(email, senha) {
    const resposta = await apiClient.post('/login/', { email: email.trim(), senha })
    token.value = resposta.token
    usuario.value = resposta.usuario
    definirToken(resposta.token)
  }

  async function sair() {
    try {
      await apiClient.post('/logout/')
    } finally {
      token.value = null
      usuario.value = null
      definirToken(null)
    }
  }

  /** @returns {Promise<{ email: string, linkSimulado?: string }>} */
  function cadastrar(dados) {
    return apiClient.post('/cadastro/', dados)
  }

  function confirmarEmail(tokenConfirmacao) {
    return apiClient.post('/confirmar-email/', { token: tokenConfirmacao })
  }

  function reenviarConfirmacao(email) {
    return apiClient.post('/reenviar-confirmacao/', { email: email.trim() })
  }

  function solicitarRecuperacao(email) {
    return apiClient.post('/recuperar-senha/', { email: email.trim() })
  }

  function redefinirSenha(tokenRedefinicao, senha) {
    return apiClient.post('/redefinir-senha/', { token: tokenRedefinicao, senha })
  }

  return {
    usuario,
    token,
    estaAutenticado,
    apelido,
    entrar,
    sair,
    cadastrar,
    confirmarEmail,
    reenviarConfirmacao,
    solicitarRecuperacao,
    redefinirSenha,
  }
})
