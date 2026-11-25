<script setup>
import cafe from '@/assets/refeicoes/cafe.png'
import almoco from '@/assets/refeicoes/almoco.png'
import jantar from '@/assets/refeicoes/jantar.png'
import { ORDEM_REFEICOES } from '@/constants/refeicoes'

/** Ilustração de cada refeição (RF17), decorativa: o nome vem sempre em texto ao lado. */
const ILUSTRACOES = { cafe, almoco, jantar }

defineProps({
  refeicao: {
    type: String,
    required: true,
    // Constante importada: o defineProps não enxerga as declaradas no setup.
    validator: (valor) => ORDEM_REFEICOES.includes(valor),
  },
  grande: { type: Boolean, default: false },
})
</script>

<template>
  <div class="ilustracao" :class="{ 'ilustracao--grande': grande }" aria-hidden="true">
    <img :src="ILUSTRACOES[refeicao]" alt="" />
  </div>
</template>

<style scoped>
.ilustracao {
  display: grid;
  place-items: center;
  width: 72px;
  height: 52px;
  flex-shrink: 0;
}

.ilustracao img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 8px 10px var(--sombra-logo-cor));
}

.ilustracao--grande {
  width: 100%;
  max-width: 290px;
  height: auto;
  aspect-ratio: 290 / 160;
}
</style>
