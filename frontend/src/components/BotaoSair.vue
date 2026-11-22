<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'

const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const router = useRouter()
const saindo = ref(false)

async function sair() {
  saindo.value = true
  try {
    await auth.sair()
  } catch (falha) {
    console.error(falha)
  } finally {
    avaliacoes.limparCache()
    saindo.value = false
    await router.push({ name: 'raiz' })
  }
}
</script>

<template>
  <button
    type="button"
    class="botao botao--contorno"
    :disabled="saindo"
    data-teste="botao-sair"
    @click="sair"
  >
    {{ saindo ? 'Saindo…' : 'Sair da conta' }}
  </button>
</template>
