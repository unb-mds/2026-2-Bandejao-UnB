<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AvisoLocalizacao from '@/components/AvisoLocalizacao.vue'
import NavegacaoTopo from '@/components/NavegacaoTopo.vue'

const ROTAS_SEM_NAVEGACAO = new Set(['boas-vindas'])

const route = useRoute()
const mostrarNavegacaoTopo = computed(
  () => Boolean(route.name) && !ROTAS_SEM_NAVEGACAO.has(route.name),
)
</script>

<template>
  <div class="app">
    <NavegacaoTopo v-if="mostrarNavegacaoTopo" />
    <div class="area-tela">
      <RouterView />
      <!-- Global: aparece no primeiro acesso, antes de qualquer tela (RF19, front 3a.1). -->
      <AvisoLocalizacao />
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

.area-tela > :deep(:not(.fundo)) {
  flex: 1;
  min-height: 0;
}

@media (min-width: 768px) {
  .area-tela {
    overflow-y: auto;
  }
}

@media (min-width: 1024px) {
  .area-tela {
    max-width: var(--largura-conteudo);
    margin: 0 auto;
  }
}
</style>
