<script setup>
import { computed } from 'vue'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ORDEM_REFEICOES, REFEICOES } from '@/constants/refeicoes'
import { diaCurto, diaMes, hojeISO } from '@/utils/datas'
import { refeicaoPadrao } from '@/utils/cardapio'
import AvaliacaoWidget from '@/components/AvaliacaoWidget.vue'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'

/**
 * Avaliações da refeição selecionada no cardápio (RF15). Sem refeição
 * selecionada, a de hoje em andamento ou a próxima. Tudo o que fala com a
 * API fica no AvaliacaoWidget (FE-09).
 */
const cardapio = useCardapioStore()
cardapio.carregarCampi()
const preferencias = usePreferenciasStore()

const campusId = computed(() => preferencias.campusId)
const temSelecao = computed(
  () =>
    Boolean(preferencias.dataSelecionada) && Boolean(REFEICOES[preferencias.refeicaoSelecionada]),
)
const data = computed(() => (temSelecao.value ? preferencias.dataSelecionada : hojeISO()))
const tipo = computed(() =>
  temSelecao.value ? preferencias.refeicaoSelecionada : refeicaoPadrao(ORDEM_REFEICOES),
)

const subtitulo = computed(() =>
  [
    cardapio.buscarCampus(campusId.value)?.nome,
    REFEICOES[tipo.value].rotulo,
    `${diaCurto(data.value)}, ${diaMes(data.value)}`,
  ]
    .filter(Boolean)
    .join(' · '),
)
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-avaliacoes fundo-escuro">
      <BotaoVoltar class="voltar" :para="{ name: 'inicio' }" />
      <h1 class="titulo-tela">Avaliações</h1>
      <p class="subtitulo">{{ subtitulo }}</p>
    </header>

    <main class="conteudo sem-barra corpo">
      <AvaliacaoWidget v-if="campusId" :campus-id="campusId" :data="data" :tipo="tipo" />
    </main>

    <NavegacaoInferior />
  </div>
</template>

<style scoped>
.cabecalho-avaliacoes {
  padding-bottom: 20px;
}

.voltar {
  margin-bottom: 16px;
}

.subtitulo {
  margin-top: 4px;
  font-size: 12px;
  color: var(--branco-40);
}

.corpo {
  padding: 16px;
}
</style>
