<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <!-- Moldura mobile: o app ocupa a tela toda no celular e fica centralizado no desktop. -->
  <div class="app">
    <RouterView />
  </div>
</template>

<style scoped>
.app {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: var(--largura-app);
  margin: 0 auto;
  overflow: hidden;
  background: var(--bege);
}

.app > :deep(*) {
  flex: 1;
  min-height: 0;
}
</style>
