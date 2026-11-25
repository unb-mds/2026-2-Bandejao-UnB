<script setup>
import { computed, onMounted, watch } from 'vue'
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
  useFilaDoCampus({ seguirSelecao: false })

// A rota exige campus (exigirCampus): aqui ele sempre existe.
const campusId = preferencias.campusId
const campus = computed(() => cardapio.buscarCampus(campusId))

const naoEncontrado = computed(
  () => (cardapio.campiCarregados && !campus.value) || cardapio.campusInexistente(campusId),
)
const falhaNosCampi = computed(
  () => Boolean(cardapio.erroCampi) && !campus.value && !cardapio.carregandoCampi,
)
watch(
  naoEncontrado,
  (inexistente) => {
    if (inexistente && preferencias.campusId === campusId) preferencias.esquecerCampus()
  },
  { immediate: true },
)
onMounted(() => cardapio.carregarCampi())
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-fila fundo-escuro">
      <BotaoVoltar
        class="voltar"
        :para="{ name: 'campus-tela', params: { campusId: String(campusId) } }"
      />
      <h1 id="titulo-fila" class="titulo-tela">Fila do RU</h1>
      <p class="subtitulo">{{ campus?.nome ?? 'Campus' }}</p>
    </header>

    <main class="conteudo sem-barra corpo">
      <div v-if="naoEncontrado" class="estado">
        <p class="estado-titulo">Campus não encontrado</p>
        <RouterLink :to="{ name: 'campus' }" class="botao botao--primario">Escolher o campus</RouterLink>
      </div>
      <div v-else-if="falhaNosCampi" class="estado" role="alert" data-teste="falha-campi">
        <p>Não foi possível carregar os campi. {{ cardapio.erroCampi }}</p>
        <button type="button" class="botao botao--primario" @click="cardapio.carregarCampi({ forcar: true })">
          Tentar novamente
        </button>
      </div>
      <p v-else-if="!campus" class="estado" role="status">Carregando campus…</p>
      <FilaView v-else
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
