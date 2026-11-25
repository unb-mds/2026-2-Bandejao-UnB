<script setup>
import { REFEICOES } from '@/constants/refeicoes'
import { formatarNota } from '@/utils/cardapio'

defineProps({
  refeicoes: { type: Array, required: true },
  selecionada: { type: String, default: null },
})

const emit = defineEmits(['escolher'])
</script>

<template>
  <div class="refeicoes" role="tablist" aria-label="Refeição">
    <button
      v-for="refeicao in refeicoes"
      :key="refeicao.tipo"
      type="button"
      role="tab"
      class="refeicao"
      :class="{ 'refeicao--ativa': refeicao.tipo === selecionada }"
      :aria-selected="refeicao.tipo === selecionada"
      :data-teste="`refeicao-${refeicao.tipo}`"
      @click="emit('escolher', refeicao.tipo)"
    >
      <span class="rotulo">{{ REFEICOES[refeicao.tipo].rotulo }}</span>
      <span class="nota">
        <template v-if="refeicao.media != null">★ {{ formatarNota(refeicao.media) }}</template>
        <template v-else>Sem nota</template>
      </span>
    </button>
  </div>
</template>

<style scoped>
.refeicoes {
  display: flex;
  border-top: 1px solid var(--branco-08);
}

.refeicao {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 0;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  border-bottom: 2px solid transparent;
  color: var(--branco-40);
  transition: all 0.15s;
}
.refeicao--ativa {
  border-color: var(--branco);
  color: var(--branco);
}

.nota {
  font-size: 10px;
  font-weight: 600;
}

/* Desktop (FE-23): pílula clara, à direita dos dias, com o horário embaixo. */
@media (min-width: 1024px) {
  .refeicoes {
    justify-self: end;
    width: min(100%, 405px);
    padding: 4px;
    border: 1px solid var(--borda);
    border-radius: var(--raio-13);
    background: var(--cartao);
  }
  .refeicao {
    align-items: flex-start;
    padding: 8px 14px;
    border: 0;
    border-radius: var(--raio-9);
    text-align: left;
    color: var(--texto-suave);
  }
  .refeicao--ativa {
    color: var(--branco);
    background: var(--verde-escuro);
  }
  .refeicao .rotulo {
    font-size: 12px;
    color: inherit;
  }
  .refeicao .nota {
    font-size: 11px;
  }
}
</style>
