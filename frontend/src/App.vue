<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import NavegacaoTopo from '@/components/NavegacaoTopo.vue'

const ROTAS_SEM_NAVEGACAO = new Set(['boas-vindas'])

const route = useRoute()
const mostrarNavegacaoTopo = computed(() => !ROTAS_SEM_NAVEGACAO.has(route.name))
</script>

<template>
  <div class="app">
    <NavegacaoTopo v-if="mostrarNavegacaoTopo" />
    <div class="area-tela">
      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--bege);
}

.area-tela {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  width: 100%;
}

.area-tela > :deep(*) {
  flex: 1;
  min-height: 0;
}

@media (min-width: 1024px) {
  .area-tela {
    max-width: var(--largura-conteudo);
    margin: 0 auto;
  }
}
</style>
