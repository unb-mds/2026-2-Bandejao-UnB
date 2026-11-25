<script setup>
import { diaCurto, diaMes } from '@/utils/datas'

defineProps({
  dias: { type: Array, required: true },
  selecionado: { type: String, default: null },
})

const emit = defineEmits(['escolher'])
</script>

<template>
  <div class="dias sem-barra" role="tablist" aria-label="Dia da semana" data-rolagem-horizontal>
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
  gap: 4px;
  overflow-x: auto;
  padding: 0 16px 12px;
}

/* As 7 abas (seg–dom) dividem a largura; em telas muito estreitas ou com zoom, `.dias` rola. */
.dia {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 0;
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

/* Desktop (FE-23): pílula clara sobre o creme, com o dia escolhido em verde. */
@media (min-width: 1024px) {
  .dias {
    justify-self: start;
    gap: 2px;
    padding: 4px;
    border: 1px solid var(--borda);
    border-radius: 13px;
    background: var(--cartao);
  }
  .dia {
    flex: 0 0 auto;
    min-width: 61px;
    padding: 7px 11px;
    border-radius: 9px;
    background: transparent;
  }
  .dia-semana {
    font-size: 11px;
    color: var(--texto-suave);
  }
  .dia-data {
    font-size: 13px;
    color: var(--texto-suave);
  }
  .dia--ativo {
    background: var(--verde-escuro);
  }
  .dia--ativo .dia-semana {
    color: var(--branco-60);
  }
  .dia--ativo .dia-data {
    color: #fff;
  }
}
</style>
