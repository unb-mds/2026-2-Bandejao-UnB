<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { AVISO_SAIR_SEM_CONFIRMACAO, useSair } from '@/composables/sair'

const auth = useAuthStore()
const router = useRouter()
const { saindo, semConfirmacao, sair } = useSair()

async function sairDaConta() {
  if (await sair()) await router.push({ name: 'raiz' })
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
      @click="sairDaConta"
    >
      {{ saindo ? 'Saindo…' : 'Sair da conta' }}
    </button>
    <p v-if="semConfirmacao" class="texto-pequeno aviso" role="alert" data-teste="sair-aviso">
      {{ AVISO_SAIR_SEM_CONFIRMACAO }}
    </p>
  </div>
</template>

<style scoped>
.aviso {
  line-height: 1.6;
  color: var(--erro-texto);
}
</style>
