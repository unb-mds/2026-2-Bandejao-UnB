<script setup>
import { CANAL_CONTATO, EMAIL_CONTATO } from '@/constants/contato'

/**
 * Canal de contato para reclamações e pedidos de exclusão da conta (RNF08,
 * RNF07.4, Visão 9.1): o e-mail da equipe por extenso, com link `mailto`.
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
  /* --texto-suave sobre o bege fica abaixo de 4,5:1 em 12 px (WCAG AA). */
  color: var(--texto-escuro);
}

.contato-equipe a {
  font-weight: 700;
  color: var(--verde-medio);
  text-decoration: underline;
  text-underline-offset: 2px;
  overflow-wrap: anywhere;
}
</style>
