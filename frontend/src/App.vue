<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AsideConta from '@/components/AsideConta.vue'
import AvisoLocalizacao from '@/components/AvisoLocalizacao.vue'
import BarraLateral from '@/components/BarraLateral.vue'
import NavegacaoTopo from '@/components/NavegacaoTopo.vue'
import PontosAviso from '@/components/PontosAviso.vue'
import { usePreferenciasStore } from '@/stores/preferencias'

const ROTAS_SEM_NAVEGACAO = new Set(['boas-vindas'])
// As telas de conta ganham, no desktop, o lado verde do protótipo (AsideConta).
const ROTAS_DE_CONTA = new Set([
  'login',
  'cadastro',
  'confirmar-email',
  'recuperar-senha',
  'redefinir-senha',
])
// No desktop (FE-23), as telas de entrada ocupam a largura toda, com o lado
// verde à esquerda e sem a lateral, como no protótipo.
const ROTAS_DE_ENTRADA = new Set(['boas-vindas', 'campus', ...ROTAS_DE_CONTA])

const route = useRoute()
const preferencias = usePreferenciasStore()
const telaDeConta = computed(() => ROTAS_DE_CONTA.has(route.name))
const mostrarNavegacaoTopo = computed(
  () => Boolean(route.name) && !ROTAS_SEM_NAVEGACAO.has(route.name),
)
// Quem chega à escolha do campus por "Trocar" já tem um campus: ali a lateral
// continua, para ter Início, voltar e o contato (RNF08).
const mostrarBarraLateral = computed(() => {
  if (!route.name) return false
  if (route.name === 'campus') return Boolean(preferencias.campusId)
  return !ROTAS_DE_ENTRADA.has(route.name)
})
</script>

<template>
  <div class="app" :class="{ 'app--lateral': mostrarBarraLateral, 'app--conta': telaDeConta }">
    <BarraLateral v-if="mostrarBarraLateral" />
    <AsideConta v-if="telaDeConta" :passo="route.name === 'cadastro' ? 2 : 1" />
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
    <!-- Global (RF24.2): o aviso "+N pontos" de qualquer contribuição, em qualquer tela. -->
    <PontosAviso />
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

/* Desktop (FE-23): a lateral fica fixa à esquerda e a tela rola ao lado
   dela; as telas de entrada ocupam a largura toda. A NavegacaoTopo some. */
@media (min-width: 1024px) {
  .app {
    background: var(--creme);
  }
  .app--lateral {
    display: grid;
    grid-template-columns: var(--largura-lateral) minmax(0, 1fr);
  }
  .app :deep(.navegacao-topo) {
    display: none;
  }
  .app--conta {
    display: grid;
    grid-template-columns: minmax(360px, 0.85fr) minmax(520px, 1.15fr);
  }
}
</style>
