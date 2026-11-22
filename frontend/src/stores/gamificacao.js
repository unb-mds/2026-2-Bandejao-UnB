import { defineStore } from 'pinia'
import { ref } from 'vue'

const ehPontuacao = (valor) => Number.isInteger(valor) && valor >= 0

const ehBlocoDePontos = (pontos) =>
  ehPontuacao(pontos?.total) &&
  ehPontuacao(pontos.contribuicao) &&
  ehPontuacao(pontos.avaliacaoLiberada)

export const useGamificacaoStore = defineStore('gamificacao', () => {
  const ultimosPontos = ref(null)
  const aviso = ref(null)
  const progressoDesatualizado = ref(false)
  let ultimoIdDoAviso = 0

  /**
   * Recebe o bloco `pontos` de uma resposta de check-in ou de avaliação
   * (RF24.2). Guarda os três campos do contrato e, com `total > 0`, abre um
   * aviso novo para o `PontosAviso`, mesmo que o total seja igual ao do
   * anterior. Um bloco fora do contrato é ignorado e vai para o console.
   */
  function registrarPontos(pontos) {
    if (!ehBlocoDePontos(pontos)) {
      console.error('Bloco pontos fora do contrato.', pontos)
      return
    }
    const { total, contribuicao, avaliacaoLiberada } = pontos
    ultimosPontos.value = { total, contribuicao, avaliacaoLiberada }
    if (total === 0) return
    ultimoIdDoAviso += 1
    aviso.value = { id: ultimoIdDoAviso, total }
    progressoDesatualizado.value = true
  }

  /**
   * Fecha o aviso aberto. Com `id`, só fecha se ele ainda for o aviso atual:
   * o temporizador de um aviso antigo não pode fechar um mais novo.
   */
  function fecharAviso(id = aviso.value?.id) {
    if (aviso.value?.id === id) aviso.value = null
  }

  function limpar() {
    ultimosPontos.value = null
    aviso.value = null
    progressoDesatualizado.value = false
  }

  return { ultimosPontos, aviso, progressoDesatualizado, registrarPontos, fecharAviso, limpar }
})

export function repassarPontos(pontos, origem) {
  try {
    useGamificacaoStore().registrarPontos(pontos)
  } catch (falha) {
    console.error(`Falha ao registrar os pontos ${origem}.`, falha)
  }
}
