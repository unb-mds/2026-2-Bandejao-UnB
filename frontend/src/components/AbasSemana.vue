<script setup>
import { diaCurto, diaMes } from '@/utils/datas'

defineProps({
  dias: { type: Array, required: true },
  selecionado: { type: String, default: null },
})

const emit = defineEmits(['escolher'])
</script>

<template>
  <div class="dias sem-barra" role="tablist" aria-label="Dia da semana">
    <button
      v-for="dia in dias"
      :key="dia"
      type="button"
      role="tab"
      class="dia"
      :class="{ 'dia--ativo': dia === selecionado }"
      :aria-selected="dia === selecionado"
      @click="emit('escolher', dia)"
    >
      <span class="dia-semana">{{ diaCurto(dia) }}</span>
      <span class="dia-data">{{ diaMes(dia) }}</span>
    </button>
  </div>
</template>

<style scoped>
.dias {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 0 16px 12px;
}

.dia {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 14px;
  border-radius: var(--raio-md);
  background: var(--branco-08);
  transition: all 0.15s;
}
.dia--ativo {
  background: #fff;
}

.dia-semana {
  font-size: 10px;
  font-weight: 600;
  color: var(--branco-45);
}
.dia--ativo .dia-semana {
  color: var(--texto-suave);
}

.dia-data {
  font-size: 12px;
  font-weight: 900;
  color: var(--branco-75);
}
.dia--ativo .dia-data {
  color: var(--verde-escuro);
}
</style>
