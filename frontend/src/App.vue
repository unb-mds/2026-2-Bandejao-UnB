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
    </div>
    <!--
      Global (RF19): camada por cima da tela atual. Abre sozinho na abertura do
      app ou por abrirAvisoLocalizacao() de qualquer tela. Fica fora da
      .area-tela porque o <dialog> não participa do layout das telas.
    -->
    <AvisoLocalizacao />
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
