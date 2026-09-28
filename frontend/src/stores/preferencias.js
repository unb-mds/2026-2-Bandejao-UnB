import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { buscarCampus, campusValido } from '@/constants/campi'
import { IDS_MARCADORES } from '@/constants/marcadores'
import { DIETAS } from '@/constants/dietas'
import { contarFiltrosAtivos, selecaoPadrao } from '@/utils/cardapio'

const CHAVE = 'bandejao:preferencias'

function lerPreferencias() {
  try {
    const salvas = JSON.parse(localStorage.getItem(CHAVE) ?? '{}')
    return {
      campusId: campusValido(salvas.campusId) ? salvas.campusId : null,
      dieta: DIETAS.some((d) => d.id === salvas.dieta) ? salvas.dieta : 'todos',
      marcadores: Array.isArray(salvas.marcadores)
        ? salvas.marcadores.filter((m) => IDS_MARCADORES.includes(m))
        : [],
    }
  } catch {
    return { campusId: null, dieta: 'todos', marcadores: [] }
  }
}

/**
 * Preferências do aparelho (RF07, RF08, RF09, RNF03): campus, filtros de
 * dieta e de marcadores ficam no localStorage; dia e refeição selecionados
 * valem só para a sessão de navegação.
 */
export const usePreferenciasStore = defineStore('preferencias', () => {
  const salvas = lerPreferencias()
  const campusId = ref(salvas.campusId)
  const dieta = ref(salvas.dieta)
  const marcadores = ref(salvas.marcadores)
  const dataSelecionada = ref(null)
  const refeicaoSelecionada = ref(null)

  const campus = computed(() => buscarCampus(campusId.value))
  const filtrosAtivos = computed(() => contarFiltrosAtivos(dieta.value, marcadores.value))

  watch(
    [campusId, dieta, marcadores],
    () => {
      try {
        localStorage.setItem(
          CHAVE,
          JSON.stringify({
            campusId: campusId.value,
            dieta: dieta.value,
            marcadores: marcadores.value,
          }),
        )
      } catch {
        // sem armazenamento local: a preferência vale só nesta visita
      }
    },
    { deep: true, flush: 'sync' },
  )

  function escolherCampus(id) {
    if (!campusValido(id)) return
    campusId.value = id
  }

  function aplicarFiltros(novaDieta, novosMarcadores) {
    dieta.value = novaDieta
    marcadores.value = [...novosMarcadores]
  }

  function selecionar(data, refeicao) {
    dataSelecionada.value = data
    refeicaoSelecionada.value = refeicao
  }

  /**
   * Garante que dia/refeição selecionados existem no cardápio da semana;
   * caso contrário aplica a seleção padrão do RF07.
   */
  function ajustarSelecao(dias, agora = new Date()) {
    const dia = dias.find((d) => d.data === dataSelecionada.value)
    if (!dia) {
      const padrao = selecaoPadrao(dias, agora)
      selecionar(padrao.data, padrao.refeicao)
      return
    }
    if (!dia.refeicoes.some((r) => r.tipo === refeicaoSelecionada.value)) {
      refeicaoSelecionada.value = dia.refeicoes[0]?.tipo ?? null
    }
  }

  return {
    campusId,
    dieta,
    marcadores,
    dataSelecionada,
    refeicaoSelecionada,
    campus,
    filtrosAtivos,
    escolherCampus,
    aplicarFiltros,
    selecionar,
    ajustarSelecao,
  }
})
