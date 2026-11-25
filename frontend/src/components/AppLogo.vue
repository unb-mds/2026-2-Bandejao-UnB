<script setup>
import logo from '@/assets/marca/bandejao-logo.png'

/**
 * Logo do Bandejão (RF17): a bandeja com salada, arroz e feijão e legumes.
 * `tamanho` é a altura da caixa; a largura é 1,55 vez a altura, como no
 * protótipo, e a bandeja se ajusta dentro dela sem distorcer.
 */
defineProps({
  tamanho: { type: Number, default: 64 },
})
</script>

<template>
  <img
    class="logo"
    :src="logo"
    :width="Math.round(tamanho * 1.55)"
    :height="tamanho"
    alt="Logo do Bandejão"
  />
</template>

<style scoped>
.logo {
  display: block;
  flex: 0 0 auto;
  object-fit: contain;
  filter: drop-shadow(0 9px 14px var(--sombra-logo));
}
</style>
