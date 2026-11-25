<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ID_CAMPUS_COM_EXECUTIVO, idDeCampusValido } from '@/constants/campi'
import { ORDEM_REFEICOES, REFEICOES } from '@/constants/refeicoes'
import { abrirAvisoLocalizacao } from '@/composables/avisoLocalizacao'
import { refeicaoPadrao } from '@/utils/cardapio'
import { hojeISO, minutosAgora, minutosDoDia } from '@/utils/datas'
import AvisoExecutivo from '@/components/AvisoExecutivo.vue'
import ContatoEquipe from '@/components/ContatoEquipe.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'
import CardapioView from './CardapioView.vue'
import FilaView from './FilaView.vue'

const props = defineProps({
  campusId: { type: String, required: true },
})

const INTERVALO_DO_RELOGIO = 30 * 1000

const route = useRoute()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()
const agora = ref(new Date())
let relogio = null

const id = computed(() => idDeCampusValido(props.campusId))
const campus = computed(() => cardapio.buscarCampus(id.value))
const naoEncontrado = computed(
  () =>
    !id.value ||
    (cardapio.campiCarregados && !campus.value) ||
    cardapio.campusInexistente(id.value),
)
const falhaNosCampi = computed(
  () => Boolean(cardapio.erroCampi) && !campus.value && !cardapio.carregandoCampi,
)
const temExecutivo = computed(() => !naoEncontrado.value && id.value === ID_CAMPUS_COM_EXECUTIVO)

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
const dataDaPrevisao = computed(() => preferencias.dataSelecionada ?? hojeISO(agora.value))
const refeicaoDaPrevisao = computed(() =>
  REFEICOES[preferencias.refeicaoSelecionada]
    ? preferencias.refeicaoSelecionada
    : refeicaoDaFila.value,
)
const mostrarPrevisao = computed(() => {
  const hoje = hojeISO(agora.value)
  if (dataDaPrevisao.value !== hoje) return dataDaPrevisao.value > hoje
  return !refeicaoEncerrada.value || refeicaoDaPrevisao.value !== refeicaoDaFila.value
})

onMounted(() => {
  cardapio.carregarCampi()
  relogio = setInterval(() => {
    agora.value = new Date()
  }, INTERVALO_DO_RELOGIO)
})

onBeforeUnmount(() => clearInterval(relogio))

watch(
  () => route.hash,
  async (hash) => {
    if (hash !== '#fila') return
    await nextTick()
    document.getElementById('fila')?.scrollIntoView?.()
  },
  { immediate: true },
)

watch(
  [campus, () => cardapio.campiCarregados],
  ([atual, carregados]) => {
    if (atual) {
      preferencias.escolherCampus(atual.id)
    } else if (carregados && id.value && id.value === preferencias.campusId) {
      preferencias.esquecerCampus()
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-tela-campus fundo-escuro">
      <div class="linha-campus">
        <h1 class="titulo-tela">{{ campus?.nome ?? 'Campus' }}</h1>
        <RouterLink :to="{ name: 'campus' }" class="acao-cabecalho">
          Trocar
          <IconeSvg nome="chevron" :tamanho="14" cor="currentColor" espessura="2.5" />
        </RouterLink>
      </div>
      <button
        type="button"
        class="acao-cabecalho usar-localizacao"
        data-teste="usar-localizacao"
        @click="abrirAvisoLocalizacao"
      >
        <IconeSvg nome="local" :tamanho="14" cor="currentColor" espessura="2.2" />
        Usar minha localização
      </button>
      <div v-if="falhaNosCampi" class="falha-campi" role="alert" data-teste="falha-campi">
        <p>Não foi possível carregar os campi. {{ cardapio.erroCampi }}</p>
        <button
          type="button"
          class="botao-pequeno"
          @click="cardapio.carregarCampi({ forcar: true })"
        >
          Tentar novamente
        </button>
      </div>
    </header>

    <AvisoExecutivo v-if="temExecutivo" />

    <main v-if="naoEncontrado" class="conteudo sem-barra estado">
      <p class="estado-titulo">Campus não encontrado</p>
      <RouterLink :to="{ name: 'campus' }" class="botao botao--primario">Escolher o campus</RouterLink>
      <ContatoEquipe />
    </main>

    <main v-else class="conteudo sem-barra">
      <CardapioView :campus-id="id" />
      <FilaView
        :campus-id="id"
        :tipo-refeicao="refeicaoDaFila"
        :encerrada="refeicaoEncerrada"
        :campus-confirmado="Boolean(campus)"
        :refeicao-previsao="refeicaoDaPrevisao"
        :data-previsao="dataDaPrevisao"
        :mostrar-previsao="mostrarPrevisao"
      />
      <ContatoEquipe />
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

.acao-cabecalho {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 700;
  color: var(--dourado);
  text-decoration: none;
}

.usar-localizacao {
  margin-top: 8px;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
}

.falha-campi {
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--branco);
}

.falha-campi .botao-pequeno {
  margin-top: 8px;
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
