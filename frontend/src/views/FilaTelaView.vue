<script setup>
import { computed, onMounted } from 'vue'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { useFilaDoCampus } from '@/composables/filaDoCampus'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import ContatoEquipe from '@/components/ContatoEquipe.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'
import FilaView from './FilaView.vue'

/**
 * Tela "Fila do RU" (RF12, RF13): a previsão de pico e o check-in do campus
 * lembrado, sem o cardápio. É o destino do item "Fila" das navegações; a
 * tela do campus continua com a mesma seção embaixo do cardápio.
 */
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()
const { refeicaoDaFila, refeicaoEncerrada, dataDaPrevisao, refeicaoDaPrevisao, mostrarPrevisao } =
  useFilaDoCampus()

// A rota exige campus (exigirCampus): aqui ele sempre existe.
const campusId = computed(() => preferencias.campusId)
const campus = computed(() => cardapio.buscarCampus(campusId.value))

onMounted(() => cardapio.carregarCampi())
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-fila fundo-escuro">
      <BotaoVoltar
        class="voltar"
        :para="{ name: 'campus-tela', params: { campusId: String(campusId) } }"
      />
      <h1 class="titulo-tela">Fila do RU</h1>
      <p class="subtitulo">{{ campus?.nome ?? 'Campus' }}</p>
    </header>

    <main class="conteudo sem-barra corpo">
      <FilaView
        :campus-id="campusId"
        :tipo-refeicao="refeicaoDaFila"
        :encerrada="refeicaoEncerrada"
        :campus-confirmado="Boolean(campus)"
        :refeicao-previsao="refeicaoDaPrevisao"
        :data-previsao="dataDaPrevisao"
        :mostrar-previsao="mostrarPrevisao"
        :titulo-visivel="false"
      />
      <ContatoEquipe />
    </main>

    <NavegacaoInferior />
  </div>
</template>

<style scoped>
.cabecalho-fila {
  padding-bottom: 20px;
}

.voltar {
  margin-bottom: 16px;
}

.subtitulo {
  margin-top: 4px;
  font-size: 13px;
  color: var(--branco-75);
}

/* A seção da fila já tem o próprio espaçamento; no desktop, a margem do
   topo dela (pensada para ficar embaixo do cardápio) sai. */
.corpo :deep(.secao-fila) {
  margin-top: 0;
}
</style>
