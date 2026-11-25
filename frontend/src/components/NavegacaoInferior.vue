<script setup>
import { useRoute } from 'vue-router'
import { ITENS_NAVEGACAO as ITENS, itemAtivo } from '@/constants/navegacao'
import IconeSvg from './IconeSvg.vue'

/**
 * Barra de navegação inferior (protótipo): visível em Cardápio, Fila e
 * Avaliações — não na Início. "Perfil" leva a Meu progresso, inclusive
 * para visitantes sem login.
 */
const route = useRoute()
const ativo = (item) => itemAtivo(item, route.name)
</script>

<template>
  <nav class="navegacao" aria-label="Navegação principal">
    <RouterLink
      v-for="item in ITENS"
      :key="item.rotulo"
      :to="{ name: item.rota }"
      class="item"
      :class="{ 'item--ativo': ativo(item) }"
      :aria-current="ativo(item) ? 'page' : undefined"
    >
      <IconeSvg
        :nome="item.icone"
        :cor="ativo(item) ? 'var(--verde-escuro)' : 'var(--texto-claro)'"
        :preenchimento="ativo(item) && item.preenche ? 'var(--verde-escuro)' : 'none'"
      />
      <span class="rotulo-item">{{ item.rotulo }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.navegacao {
  flex-shrink: 0;
  display: flex;
  background: var(--branco);
  border-top: 1px solid var(--borda);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 0;
  text-decoration: none;
  transition: transform 0.15s;
}
.item:active {
  transform: scale(0.95);
}
@media (hover: hover) {
  .item:hover .rotulo-item {
    color: var(--verde-escuro);
  }
}

@media (min-width: 768px) {
  .navegacao {
    display: none;
  }
}

.rotulo-item {
  font-size: 9px;
  font-weight: 700;
  color: var(--texto-claro);
}
.item--ativo .rotulo-item {
  color: var(--verde-escuro);
}
</style>
