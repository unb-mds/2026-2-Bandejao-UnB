import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { idDeCampusValido } from '@/constants/campi'
import { IDS_MARCADORES, MARCADORES_ANTIGOS } from '@/constants/marcadores'
import { DIETA_PADRAO, DIETAS, DIETAS_ANTIGAS } from '@/constants/dietas'
import { contarFiltrosAtivos, selecaoPadrao } from '@/utils/cardapio'

const CHAVE = 'bandejao:preferencias'

/** Só a leitura e o parse ficam no try: erro na validação não pode passar por "sem dados". */
function lerSalvas() {
  try {
    const salvas = JSON.parse(localStorage.getItem(CHAVE) ?? '{}')
    return salvas && typeof salvas === 'object' ? salvas : {}
  } catch (falha) {
    console.warn('Preferências salvas ilegíveis; usando os padrões.', falha)
    return {}
  }
}

function lerPreferencias() {
  const salvas = lerSalvas()
  const dieta = DIETAS_ANTIGAS[salvas.dieta] ?? salvas.dieta
  return {
    campusId: Number.isInteger(salvas.campusId) ? idDeCampusValido(salvas.campusId) : null,
    dieta: DIETAS.some((d) => d.id === dieta) ? dieta : DIETA_PADRAO,
    marcadores: Array.isArray(salvas.marcadores)
      ? salvas.marcadores
          .map((m) => MARCADORES_ANTIGOS[m] ?? m)
          .filter((m) => IDS_MARCADORES.includes(m))
      : [],
    avisoLocalizacaoAdiado: salvas.avisoLocalizacaoAdiado === true,
    localizacaoPermitida: salvas.localizacaoPermitida === true,
  }
}

/**
 * Preferências do aparelho (RF07, RF08, RF09, RF19, RNF03): campus, filtros
 * de dieta e de marcadores, o "Agora não" do aviso de localização e, para
 * navegadores sem Permissions API, a marca de que a pessoa já permitiu a
 * localização ficam no localStorage; dia e refeição selecionados valem só
 * para a sessão de navegação.
 */
export const usePreferenciasStore = defineStore('preferencias', () => {
  const salvas = lerPreferencias()
  const campusId = ref(salvas.campusId)
  const dieta = ref(salvas.dieta)
  const marcadores = ref(salvas.marcadores)
  const avisoLocalizacaoAdiado = ref(salvas.avisoLocalizacaoAdiado)
  const localizacaoPermitida = ref(salvas.localizacaoPermitida)
  let falhaDeEscritaAvisada = false
  const dataSelecionada = ref(null)
  const refeicaoSelecionada = ref(null)

  const filtrosAtivos = computed(() => contarFiltrosAtivos(dieta.value, marcadores.value))

  watch(
    [campusId, dieta, marcadores, avisoLocalizacaoAdiado, localizacaoPermitida],
    () => {
      try {
        localStorage.setItem(
          CHAVE,
          JSON.stringify({
            campusId: campusId.value,
            dieta: dieta.value,
            marcadores: marcadores.value,
            avisoLocalizacaoAdiado: avisoLocalizacaoAdiado.value,
            localizacaoPermitida: localizacaoPermitida.value,
          }),
        )
      } catch (falha) {
        // Sem armazenamento local (ex.: modo privado sem cota): vale só nesta visita.
        if (!falhaDeEscritaAvisada) {
          falhaDeEscritaAvisada = true
          console.warn('Não foi possível salvar as preferências neste aparelho.', falha)
        }
      }
    },
    { deep: true, flush: 'sync' },
  )

  function escolherCampus(valor) {
    const id = idDeCampusValido(valor)
    if (id) campusId.value = id
  }

  function aplicarFiltros(novaDieta, novosMarcadores) {
    dieta.value = novaDieta
    marcadores.value = [...novosMarcadores]
  }

  /** "Agora não" do aviso de localização: não reaparece a cada abertura (RF19). */
  function adiarAvisoLocalizacao() {
    avisoLocalizacaoAdiado.value = true
  }

  /** Para navegadores sem Permissions API: lembra que a pessoa já permitiu (RF19). */
  function registrarLocalizacaoPermitida() {
    localizacaoPermitida.value = true
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
    avisoLocalizacaoAdiado,
    localizacaoPermitida,
    dataSelecionada,
    refeicaoSelecionada,
    filtrosAtivos,
    escolherCampus,
    aplicarFiltros,
    adiarAvisoLocalizacao,
    registrarLocalizacaoPermitida,
    selecionar,
    ajustarSelecao,
  }
})
