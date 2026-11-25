<script setup>
import { computed, watch } from 'vue'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ORDEM_REFEICOES, REFEICOES } from '@/constants/refeicoes'
import { diaCurto, diaMes, hojeISO } from '@/utils/datas'
import { refeicaoPadrao } from '@/utils/cardapio'
import AvaliacaoWidget from '@/components/AvaliacaoWidget.vue'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'

/**
 * Avaliações da refeição selecionada no cardápio (RF15). Tudo o que fala com
 * a API sobre a refeição fica no AvaliacaoWidget.
 *
 * Qual refeição abre: o dia selecionado (ou hoje) e a refeição selecionada,
 * se o campus a serve nesse dia. Senão, entre as refeições servidas (do
 * resumo do dia), a em andamento ou a próxima, se o dia é hoje, ou a
 * primeira do dia.
 */
const avaliacoes = useAvaliacoesStore()
const cardapio = useCardapioStore()
cardapio.carregarCampi()
const preferencias = usePreferenciasStore()

const campusId = computed(() => preferencias.campusId)
const data = computed(() => preferencias.dataSelecionada || hojeISO())
const tiposServidos = computed(
  () => avaliacoes.daResumoDoDia(campusId.value, data.value)?.map((r) => r.tipo) ?? null,
)
const tipo = computed(() => {
  const escolhida = preferencias.refeicaoSelecionada
  const servidos = tiposServidos.value
  if (REFEICOES[escolhida] && (!servidos || servidos.includes(escolhida))) return escolhida
  const tipos = servidos?.length ? servidos : ORDEM_REFEICOES
  return data.value === hojeISO() ? refeicaoPadrao(tipos) : tipos[0]
})

watch(
  [campusId, data],
  ([campus, dia]) => {
    if (campus && [null, 'erro'].includes(avaliacoes.situacaoDoResumoDoDia(campus, dia))) {
      avaliacoes.carregarResumoDoDia(campus, dia)
    }
  },
  { immediate: true },
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
      <!-- :key: outra refeição é outro widget, sem estado nem envio da anterior. -->
      <AvaliacaoWidget
        v-if="campusId"
        :key="`${campusId}|${data}|${tipo}`"
        :campus-id="campusId"
        :data="data"
        :tipo="tipo"
      />
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

@media (min-width: 1024px) {
  .corpo {
    padding: 27px clamp(28px, 4vw, 62px) 50px;
  }
}
</style>
