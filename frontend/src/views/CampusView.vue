<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { CAMPUS_COM_EXECUTIVO, idDeCampusValido } from '@/constants/campi'
import { ORDEM_REFEICOES, REFEICOES } from '@/constants/refeicoes'
import { refeicaoPadrao } from '@/utils/cardapio'
import { hojeISO, minutosAgora, minutosDoDia } from '@/utils/datas'
import AvisoExecutivo from '@/components/AvisoExecutivo.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'
import CardapioView from './CardapioView.vue'
import FilaView from './FilaView.vue'

const props = defineProps({
  campusId: { type: String, required: true },
})

const route = useRoute()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()
const agora = ref(new Date())

const id = computed(() => idDeCampusValido(props.campusId))
const campus = computed(() => cardapio.buscarCampus(id.value))
const naoEncontrado = computed(() => !id.value || (cardapio.campiCarregados && !campus.value))
const temExecutivo = computed(() => campus.value?.nome === CAMPUS_COM_EXECUTIVO)

const refeicaoDaFila = computed(() => {
  const selecionada = preferencias.refeicaoSelecionada
  if (preferencias.dataSelecionada === hojeISO(agora.value) && REFEICOES[selecionada]) {
    return selecionada
  }
  return refeicaoPadrao(ORDEM_REFEICOES, agora.value)
})
const refeicaoEncerrada = computed(
  () => minutosAgora(agora.value) > minutosDoDia(REFEICOES[refeicaoDaFila.value].fim),
)

onMounted(async () => {
  cardapio.carregarCampi()
  if (route.hash === '#fila') {
    await nextTick()
    document.getElementById('fila')?.scrollIntoView?.()
  }
})

watch(
  campus,
  (atual) => {
    if (atual) preferencias.escolherCampus(atual.id)
  },
  { immediate: true },
)
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-tela-campus fundo-escuro">
      <div class="linha-campus">
        <h1 class="titulo-tela">{{ campus?.nome ?? 'Campus' }}</h1>
        <RouterLink :to="{ name: 'campus' }" class="trocar">
          Trocar
          <IconeSvg nome="chevron" :tamanho="14" cor="currentColor" espessura="2.5" />
        </RouterLink>
      </div>
    </header>

    <AvisoExecutivo v-if="temExecutivo" />

    <main v-if="naoEncontrado" class="conteudo sem-barra estado">
      <p class="estado-titulo">Campus não encontrado</p>
      <RouterLink :to="{ name: 'campus' }" class="botao botao--primario">Escolher o campus</RouterLink>
    </main>

    <main v-else class="conteudo sem-barra">
      <CardapioView :campus-id="id" />
      <FilaView :campus-id="id" :tipo-refeicao="refeicaoDaFila" :encerrada="refeicaoEncerrada" />
    </main>

    <NavegacaoInferior />
  </div>
</template>

<style scoped>
.cabecalho-tela-campus {
  padding-bottom: 16px;
}

.linha-campus {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.trocar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 700;
  color: var(--dourado);
  text-decoration: none;
}

.estado {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px 20px;
  text-align: center;
}

.estado-titulo {
  font-family: var(--fonte-titulo);
  font-size: 16px;
  font-weight: 700;
  color: var(--texto-escuro);
}
</style>
