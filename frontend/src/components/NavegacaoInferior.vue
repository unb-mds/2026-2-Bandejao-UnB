<script setup>
import { useRoute } from 'vue-router'
import IconeSvg from './IconeSvg.vue'

/**
 * Barra de navegação inferior (protótipo): visível em Cardápio, Fila e
 * Avaliações — não na Início. "Perfil" leva à Início, onde ficam o apelido,
 * a troca de campus e o login/logout.
 */
const ITENS = [
  { rotulo: 'Início', rota: 'inicio', icone: 'casa', preenche: true },
  { rotulo: 'Cardápio', rota: 'cardapio', icone: 'talheres' },
  { rotulo: 'Fila', rota: 'fila', icone: 'relogio' },
  { rotulo: 'Avaliações', rota: 'avaliacoes', icone: 'estrela', preenche: true },
  { rotulo: 'Perfil', rota: 'inicio', icone: 'usuario' },
]

const route = useRoute()

// Como no protótipo, "Início" e "Perfil" nunca aparecem como ativos.
const ativo = (item) => item.rota !== 'inicio' && route.name?.toString().startsWith(item.rota)
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
  background: #fff;
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

.rotulo-item {
  font-size: 9px;
  font-weight: 700;
  color: var(--texto-claro);
}
.item--ativo .rotulo-item {
  color: var(--verde-escuro);
}
</style>
