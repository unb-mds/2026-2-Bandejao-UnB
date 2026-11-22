<script setup>
import { CANAL_CONTATO, EMAIL_CONTATO } from '@/constants/contato'

/**
 * Canal de contato para reclamações (RNF08, Visão 9.1), visível sem login e
 * em qualquer largura. No celular a barra do topo some, então é aqui que o
 * contato fica à vista.
 */
</script>

<template>
  <footer class="contato-equipe" data-teste="contato-equipe">
    <p>
      Dúvidas, reclamações ou pedido de exclusão da conta? Escreva para
      <a :href="CANAL_CONTATO">{{ EMAIL_CONTATO }}</a
      >.
    </p>
  </footer>
</template>

<style scoped>
.contato-equipe {
  padding: 24px 16px 32px;
  text-align: center;
  font-size: 12px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.contato-equipe a {
  font-weight: 700;
  color: var(--verde-medio);
  text-decoration: underline;
  text-underline-offset: 2px;
  overflow-wrap: anywhere;
}
</style>
