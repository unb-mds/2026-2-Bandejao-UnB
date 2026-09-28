<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <strong>Bandejão</strong>
    <nav style="display: flex; gap: 1rem">
      <RouterLink :to="{ name: 'cardapio' }">Cardápio</RouterLink>
      <RouterLink :to="{ name: 'fila' }">Fila</RouterLink>
      <RouterLink :to="{ name: 'avaliacoes' }">Avaliações</RouterLink>
      <RouterLink :to="{ name: 'login' }">Entrar</RouterLink>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>
