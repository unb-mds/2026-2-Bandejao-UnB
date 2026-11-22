import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'

export const AVISO_SAIR_SEM_CONFIRMACAO =
  'Saímos deste aparelho, mas o servidor não confirmou. Se o aparelho for compartilhado, ' +
  'recarregue a página com internet e saia de novo.'

/**
 * Sair da conta (RF03.3), do `BotaoSair` e do menu da Início. `sair()` devolve
 * `true` se o servidor confirmou, `false` se não confirmou (a conta sai só
 * deste aparelho e `semConfirmacao` liga o aviso) e `null` se já estava saindo.
 */export function useSair() {
  const auth = useAuthStore()
  const avaliacoes = useAvaliacoesStore()
  const saindo = ref(false)
  const semConfirmacao = ref(false)

  async function sair() {
    if (saindo.value) return null
    saindo.value = true
    semConfirmacao.value = false
    try {
      await auth.sair()
      return true
    } catch (falha) {
      console.error(falha)
      semConfirmacao.value = true
      return false
    } finally {
      avaliacoes.limparCache()
      saindo.value = false
    }
  }

  return { saindo, semConfirmacao, sair }
}
