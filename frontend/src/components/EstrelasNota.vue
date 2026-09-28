<script setup>
import { computed } from 'vue'
import IconeSvg from './IconeSvg.vue'

const props = defineProps({
  valor: { type: Number, default: 0 },
  tamanho: { type: Number, default: 14 },
})

const cheias = computed(() => Math.round(props.valor))
</script>

<template>
  <div class="estrelas" role="img" :aria-label="`Nota ${valor.toFixed(1)} de 5`">
    <IconeSvg
      v-for="i in 5"
      :key="i"
      nome="estrela"
      :tamanho="tamanho"
      :cor="i <= cheias ? 'var(--dourado)' : 'var(--borda-estrela)'"
      :preenchimento="i <= cheias ? 'var(--dourado)' : 'none'"
    />
  </div>
</template>

<style scoped>
.estrelas {
  display: flex;
  gap: 2px;
}
</style>
