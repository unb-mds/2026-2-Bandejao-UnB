<script setup>
import BotaoVoltar from './BotaoVoltar.vue'

/** Cabeçalho verde das telas de conta (login, cadastro, senha, e-mail). */
defineProps({
  titulo: { type: String, required: true },
  subtitulo: { type: String, default: '' },
  voltarPara: { type: [String, Object], required: true },
})
</script>

<template>
  <header class="cabecalho">
    <BotaoVoltar :para="voltarPara" historico com-rotulo />
    <h1 class="titulo-tela">{{ titulo }}</h1>
    <p v-if="subtitulo" class="subtitulo-tela">{{ subtitulo }}</p>
  </header>
</template>
