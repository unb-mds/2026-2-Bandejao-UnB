<script setup>
import { useRoute } from 'vue-router'
import IconeSvg from './IconeSvg.vue'

/**
 * Convite ao login exibido no lugar de uma ação restrita (RF05): o
 * visitante vê o motivo e um atalho para entrar, em vez de um erro.
 */
defineProps({
  titulo: { type: String, required: true },
  texto: { type: String, required: true },
})

const route = useRoute()
</script>

<template>
  <div class="cartao cartao--tracejado convite">
    <div class="icone-caixa">
      <IconeSvg nome="cadeado" :tamanho="20" cor="var(--texto-suave)" />
    </div>
    <div class="textos">
      <p class="titulo">{{ titulo }}</p>
      <p class="texto">{{ texto }}</p>
    </div>
    <RouterLink :to="{ name: 'login', query: { voltar: route.fullPath } }" class="botao-pequeno">
      Entrar
    </RouterLink>
  </div>
</template>

<style scoped>
.convite {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.icone-caixa {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--bege);
}

.textos {
  flex: 1;
}

.titulo {
  font-size: 14px;
  font-weight: 600;
  color: var(--texto-escuro);
}

.texto {
  margin-top: 2px;
  font-size: 12px;
  color: var(--texto-claro);
}
</style>
