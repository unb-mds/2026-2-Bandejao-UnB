<script setup>
import { ref } from 'vue'
import CampoTexto from './CampoTexto.vue'
import IconeSvg from './IconeSvg.vue'

defineProps({
  rotulo: { type: String, default: 'Senha' },
  dica: { type: String, default: '' },
  placeholder: { type: String, default: 'Mínimo 8 caracteres' },
  autocomplete: { type: String, default: 'current-password' },
})

const senha = defineModel({ type: String, default: '' })
const visivel = ref(false)
</script>

<template>
  <CampoTexto
    v-model="senha"
    :rotulo="rotulo"
    :dica="dica"
    :type="visivel ? 'text' : 'password'"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    com-acao
  >
    <template #acao>
      <button
        type="button"
        class="alternar"
        :aria-label="visivel ? 'Ocultar senha' : 'Mostrar senha'"
        @click="visivel = !visivel"
      >
        <IconeSvg :nome="visivel ? 'olho-fechado' : 'olho'" :tamanho="18" />
      </button>
    </template>
  </CampoTexto>
</template>

<style scoped>
.alternar {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--texto-claro);
}
</style>
