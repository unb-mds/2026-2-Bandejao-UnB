<script setup>
import { useRouter } from 'vue-router'
import IconeSvg from './IconeSvg.vue'

const props = defineProps({
  /** Destino quando não há página anterior no histórico (ou se `historico` for false). */
  para: { type: [String, Object], required: true },
  /** Volta pelo histórico do navegador quando houver página anterior dentro do app. */
  historico: { type: Boolean, default: false },
  /** Exibe o texto "Voltar" ao lado da seta (telas de autenticação). */
  comRotulo: { type: Boolean, default: false },
})

const router = useRouter()

function voltar() {
  if (props.historico && window.history.state?.back) router.back()
  else router.push(props.para)
}
</script>

<template>
  <button
    type="button"
    class="voltar"
    :class="{ 'voltar--rotulo': comRotulo }"
    aria-label="Voltar"
    @click="voltar"
  >
    <IconeSvg nome="voltar" :tamanho="comRotulo ? 20 : 22" espessura="2.5" />
    <span v-if="comRotulo">Voltar</span>
  </button>
</template>

<style scoped>
.voltar {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--branco-55);
  transition: opacity 0.15s;
}
.voltar:active {
  opacity: 0.6;
}
.voltar--rotulo {
  margin-bottom: 20px;
  color: var(--branco-60);
  font-size: 14px;
}
</style>
