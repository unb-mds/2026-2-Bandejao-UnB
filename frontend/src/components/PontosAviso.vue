<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { useGamificacaoStore } from '@/stores/gamificacao'

const DURACAO_DO_AVISO = 4000

const gamificacao = useGamificacaoStore()
let temporizador = null

const texto = computed(() => {
  const total = gamificacao.aviso?.total ?? 0
  return `+${total} ${total === 1 ? 'ponto' : 'pontos'}`
})

watch(
  () => gamificacao.aviso?.id,
  (id) => {
    clearTimeout(temporizador)
    if (id) temporizador = setTimeout(() => gamificacao.fecharAviso(id), DURACAO_DO_AVISO)
  },
  { immediate: true },
)

onBeforeUnmount(() => clearTimeout(temporizador))
</script>

<template>
  <div class="pontos-aviso" :class="{ 'pontos-aviso--aberto': gamificacao.aviso }">
    <p class="texto" role="status" aria-live="polite">
      <span v-if="gamificacao.aviso" :key="gamificacao.aviso.id" data-teste="pontos-aviso">
        <span class="estrela" aria-hidden="true">★</span>
        {{ texto }}
      </span>
    </p>
    <button
      v-if="gamificacao.aviso"
      type="button"
      class="fechar"
      aria-label="Fechar o aviso de pontos"
      data-teste="pontos-aviso-fechar"
      @click="gamificacao.fecharAviso()"
    >
      ×
    </button>
  </div>
</template>

<style scoped>
.pontos-aviso {
  position: fixed;
  left: 50%;
  /* 76px: acima da NavegacaoInferior; se a altura da barra mudar, muda aqui. */
  bottom: calc(76px + env(safe-area-inset-bottom, 0px));
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 10px;
  width: max-content;
  max-width: calc(100% - 32px);
  transform: translateX(-50%);
  pointer-events: none;
}

.pontos-aviso--aberto {
  padding: 10px 8px 10px 16px;
  border-radius: var(--raio-xl);
  background: var(--verde-escuro);
  color: var(--branco);
  box-shadow: var(--sombra-flutuante);
  pointer-events: auto;
  animation: entrar 0.2s ease-out;
}

.texto {
  margin: 0;
  font-family: var(--fonte-titulo);
  font-weight: 800;
  font-size: 15px;
}

.estrela {
  margin-right: 6px;
  color: var(--dourado);
  font-size: 18px;
  line-height: 1;
}

.fechar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.fechar:focus-visible {
  outline: 2px solid var(--dourado);
  outline-offset: 2px;
}

@media (min-width: 768px) {
  .pontos-aviso {
    bottom: 32px;
  }
}

@keyframes entrar {
  from {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pontos-aviso--aberto {
    animation: none;
  }
}
</style>
