<script setup>
import AppLogo from '@/components/AppLogo.vue'
</script>

<template>
  <div class="nao-encontrada">
    <AppLogo :tamanho="72" />
    <h1 class="titulo-tela titulo">Página não encontrada</h1>
    <p class="texto">O endereço que você abriu não existe no Bandejão.</p>
    <RouterLink :to="{ path: '/' }" class="botao botao--destaque">Voltar ao início</RouterLink>
  </div>
</template>

<style scoped>
.nao-encontrada {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 100%;
  padding: 32px 24px;
  text-align: center;
  background: var(--verde-escuro);
}

.titulo {
  margin-top: 12px;
}

.texto {
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--branco-45);
}

.botao {
  max-width: 280px;
}
</style>
