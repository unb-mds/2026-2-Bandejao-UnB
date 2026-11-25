import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ORDEM_REFEICOES, REFEICOES } from '@/constants/refeicoes'
import { refeicaoPadrao } from '@/utils/cardapio'
import { hojeISO, minutosAgora, minutosDoDia } from '@/utils/datas'

const INTERVALO_DO_RELOGIO = 30 * 1000

/**
 * Refeição do check-in e da previsão da fila (RF12, RF13), com um relógio que
 * anda a cada 30 s para a refeição virar sozinha. Usado pela tela do campus
 * (seção da fila) e pela tela "Fila do RU", que mostram a mesma coisa.
 */
export function useFilaDoCampus() {
  const preferencias = usePreferenciasStore()
  const agora = ref(new Date())
  let relogio = null

  onMounted(() => {
    relogio = setInterval(() => {
      agora.value = new Date()
    }, INTERVALO_DO_RELOGIO)
  })
  onBeforeUnmount(() => clearInterval(relogio))

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

  return { refeicaoDaFila, refeicaoEncerrada, dataDaPrevisao, refeicaoDaPrevisao, mostrarPrevisao }
}
