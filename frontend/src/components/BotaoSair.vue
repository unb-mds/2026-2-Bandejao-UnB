<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'

const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const router = useRouter()
const saindo = ref(false)
const semConfirmacao = ref(false)

async function sair() {
  if (saindo.value) return
  saindo.value = true
  semConfirmacao.value = false
  try {
    await auth.sair()
    avaliacoes.limparCache()
    await router.push({ name: 'raiz' })
  } catch (falha) {
    console.error(falha)
    avaliacoes.limparCache()
    semConfirmacao.value = true
  } finally {
    saindo.value = false
  }
}
</script>

<template>
  <div v-if="auth.estaAutenticado || semConfirmacao" class="botao-sair pilha-3">
    <button
      v-if="auth.estaAutenticado"
      type="button"
      class="botao botao--contorno"
      :disabled="saindo"
      data-teste="botao-sair"
      @click="sair"
    >
      {{ saindo ? 'Saindo…' : 'Sair da conta' }}
    </button>
    <p v-if="semConfirmacao" class="texto-pequeno aviso" role="alert" data-teste="sair-aviso">
      Saímos deste aparelho, mas o servidor não confirmou. Se o aparelho for compartilhado,
      recarregue a página com internet e saia de novo.
    </p>
  </div>
</template>

<style scoped>
.aviso {
  line-height: 1.6;
  color: var(--erro-texto);
}
</style>
