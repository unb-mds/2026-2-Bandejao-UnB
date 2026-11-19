<script setup>
import { useRoute } from 'vue-router'
import { CANAL_CONTATO } from '@/constants/contato'
import { ITENS_NAVEGACAO, itemAtivo } from '@/constants/navegacao'
import AppLogo from './AppLogo.vue'

const route = useRoute()
const ativo = (item) => itemAtivo(item, route.name)
</script>

<template>
  <div class="navegacao-topo">
    <div class="barra">
      <RouterLink :to="{ name: 'raiz' }" class="marca">
        <AppLogo :tamanho="28" />
        <span>Bandejão</span>
      </RouterLink>

      <nav class="itens" aria-label="Navegação principal">
        <RouterLink
          v-for="item in ITENS_NAVEGACAO"
          :key="item.rotulo"
          :to="{ name: item.rota }"
          class="item"
          :class="{ 'item--ativo': ativo(item) }"
          :aria-current="ativo(item) ? 'page' : undefined"
        >
          {{ item.rotulo }}
        </RouterLink>
        <a
          :href="CANAL_CONTATO"
          target="_blank"
          rel="noopener noreferrer"
          class="item item--contato"
        >
          Contato
        </a>
      </nav>
    </div>
  </div>
</template>

<style scoped>
.navegacao-topo {
  display: none;
  flex-shrink: 0;
  background: var(--verde-mais-escuro);
}

@media (min-width: 768px) {
  .navegacao-topo {
    display: block;
  }
}

.barra {
  display: flex;
  align-items: center;
  gap: 24px;
  max-width: var(--largura-conteudo);
  margin: 0 auto;
  padding: 12px 32px;
}

.marca {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 18px;
  color: #fff;
  text-decoration: none;
}

.itens {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.item {
  padding: 8px 12px;
  border-radius: var(--raio-sm);
  font-weight: 700;
  font-size: 14px;
  color: var(--branco-70);
  text-decoration: none;
  transition:
    background 0.15s,
    color 0.15s;
}

.item--ativo {
  color: #fff;
  background: var(--branco-10);
}

.item--contato {
  margin-left: 8px;
  color: var(--dourado);
}

@media (hover: hover) {
  .item:hover {
    color: #fff;
    background: var(--branco-08);
  }
  .marca:hover {
    color: var(--branco-90);
  }
}
</style>
