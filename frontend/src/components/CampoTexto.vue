<script setup>
import { useId } from 'vue'

defineOptions({ inheritAttrs: false })

defineProps({
  rotulo: { type: String, required: true },
  dica: { type: String, default: '' },
  /** Reserva espaço à direita para um botão dentro do campo (ex.: mostrar senha). */
  comAcao: { type: Boolean, default: false },
})

const valor = defineModel({ type: String, default: '' })
const id = useId()
</script>

<template>
  <div>
    <label class="rotulo campo-rotulo" :for="id">{{ rotulo }}</label>
    <div class="campo-caixa">
      <input
        :id="id"
        v-model="valor"
        class="campo-entrada"
        :class="{ 'campo-entrada--com-acao': comAcao }"
        :aria-describedby="dica ? `${id}-dica` : undefined"
        v-bind="$attrs"
      />
      <slot name="acao" />
    </div>
    <p v-if="dica" :id="`${id}-dica`" class="campo-dica">{{ dica }}</p>
  </div>
</template>

<style scoped>
.campo-rotulo {
  margin-bottom: 6px;
}

.campo-caixa {
  position: relative;
}

.campo-entrada {
  width: 100%;
  padding: 14px 16px;
  border-radius: var(--raio-md);
  font-size: 14px;
  background: var(--cartao);
  border: 1.5px solid var(--borda);
  color: var(--texto-escuro);
  transition: border-color 0.15s;
}
.campo-entrada::placeholder {
  color: var(--texto-claro);
}
.campo-entrada:focus {
  outline: none;
  border-color: var(--verde-escuro);
}
.campo-entrada--com-acao {
  padding-right: 48px;
}

.campo-dica {
  margin-top: 4px;
  font-size: 11px;
  color: var(--texto-claro);
}
</style>
