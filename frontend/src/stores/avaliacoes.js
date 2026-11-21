import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError, apiClient, mensagemDeErro } from '@/services/apiClient'

const chaveRefeicao = ({ campus, data, refeicao }) => `${campus}|${data}|${refeicao}`

const MENSAGEM_INDISPONIVEL_NO_SERVIDOR =
  'As avaliações ainda não estão disponíveis. Tente de novo mais tarde.'

/**
 * Mensagem e desfecho por `codigo` do POST /api/avaliacoes/ (contrato da
 * BE-13). 'indisponivel' troca o formulário pelo motivo; 'erro' fica no
 * formulário para a pessoa corrigir ou tentar de novo.
 */
const FALHAS_DO_ENVIO = {
  janela_avaliacao_fechada: {
    desfecho: 'indisponivel',
    mensagem:
      'A avaliação desta refeição está fechada. Só dá para avaliar refeições de hoje que já começaram, até 23h59.',
  },
  refeicao_nao_encontrada: {
    desfecho: 'indisponivel',
    mensagem: 'Esta refeição não está no cardápio, então não pode ser avaliada.',
  },
  nota_invalida: { desfecho: 'erro', mensagem: 'Escolha uma nota de 1 a 5 estrelas.' },
  comentario_muito_longo: {
    desfecho: 'erro',
    mensagem: 'O comentário pode ter no máximo 500 caracteres.',
  },
}

/**
 * Avaliações das refeições (RF15, front 3b).
 *
 * Contrato da BE-13 (FE-09): o resumo do dia dá o `refeicaoId` de cada
 * refeição; `GET /api/refeicoes/{refeicaoId}/avaliacoes/` dá a média, a
 * quantidade e os comentários; `POST /api/avaliacoes/` cria ou edita (upsert).
 *
 * O contrato não tem "minha avaliação": ela vem da resposta do POST e, depois
 * de recarregar a página, do comentário com o apelido da sessão (o apelido é
 * único). `carregar`, `carregarResumo` e `daRefeicao` são do formato do MVP,
 * ainda usados pela HomeView: saem na FE-E2.
 */
export const useAvaliacoesStore = defineStore('avaliacoes', () => {
  const porRefeicao = ref({})
  const resumoPorCampus = ref({})
  /** refeicaoId → `{ resumoAvaliacoes, comentarios }` (schema AvaliacoesDaRefeicao). */
  const daRefeicaoPorId = ref({})
  /** refeicaoId → 'carregando' | 'carregado' | 'indisponivel' (501) | 'erro'. */
  const situacaoPorId = ref({})
  const erroPorId = ref({})
  /** refeicaoId → `{ nota, comentario }` da resposta do POST, nesta sessão. */
  const minhasPorId = ref({})
  const resumoDoDia = ref({})
  const situacaoDoResumo = ref({})
  const erro = ref(null)

  function daResumoDoDia(campus, data) {
    return resumoDoDia.value[`${campus}|${data}`] ?? null
  }

  function situacaoDoResumoDoDia(campus, data) {
    return situacaoDoResumo.value[`${campus}|${data}`] ?? null
  }

  async function carregarResumoDoDia(campus, data) {
    const parametros = new URLSearchParams({ campus: String(campus), data })
    const chave = `${campus}|${data}`
    situacaoDoResumo.value[chave] = 'carregando'
    try {
      resumoDoDia.value[chave] = await apiClient.get(`/avaliacoes/resumo/?${parametros}`)
      situacaoDoResumo.value[chave] = 'carregado'
    } catch (falha) {
      if (falha?.status === 501) {
        situacaoDoResumo.value[chave] = 'indisponivel'
      } else {
        console.error('Falha ao carregar o resumo do dia:', falha)
        situacaoDoResumo.value[chave] = 'erro'
      }
    }
    return daResumoDoDia(campus, data)
  }

  function daRefeicao(alvo) {
    return porRefeicao.value[chaveRefeicao(alvo)] ?? null
  }

  async function carregar(alvo) {
    erro.value = null
    const parametros = new URLSearchParams(alvo).toString()
    try {
      porRefeicao.value[chaveRefeicao(alvo)] = await apiClient.get(`/avaliacoes/?${parametros}`)
    } catch (falha) {
      erro.value = mensagemDeErro(falha)
    }
    return daRefeicao(alvo)
  }

  async function carregarResumo(campus) {
    try {
      resumoPorCampus.value[campus] = await apiClient.get(`/avaliacoes/resumo/?campus=${campus}`)
    } catch (falha) {
      erro.value = mensagemDeErro(falha)
    }
    return resumoPorCampus.value[campus] ?? null
  }

  function avaliacoesDaRefeicao(refeicaoId) {
    return daRefeicaoPorId.value[refeicaoId] ?? null
  }

  function situacaoDaRefeicao(refeicaoId) {
    return situacaoPorId.value[refeicaoId] ?? null
  }

  function erroDaRefeicao(refeicaoId) {
    return erroPorId.value[refeicaoId] ?? null
  }

  /** GET /api/refeicoes/{refeicaoId}/avaliacoes/ (público). */
  async function carregarAvaliacoesDaRefeicao(refeicaoId) {
    situacaoPorId.value[refeicaoId] = 'carregando'
    erroPorId.value[refeicaoId] = null
    try {
      daRefeicaoPorId.value[refeicaoId] = await apiClient.get(
        `/refeicoes/${refeicaoId}/avaliacoes/`,
      )
      situacaoPorId.value[refeicaoId] = 'carregado'
    } catch (falha) {
      // 501: o backend ainda não tem a BE-13. Não é erro de quem usa.
      if (falha?.status === 501) {
        situacaoPorId.value[refeicaoId] = 'indisponivel'
      } else {
        situacaoPorId.value[refeicaoId] = 'erro'
        erroPorId.value[refeicaoId] = mensagemDeErro(falha)
      }
    }
    return avaliacoesDaRefeicao(refeicaoId)
  }

  /** A avaliação da própria conta nesta refeição, ou null. */
  function minhaAvaliacao(refeicaoId, apelido) {
    if (minhasPorId.value[refeicaoId]) return minhasPorId.value[refeicaoId]
    if (!apelido) return null
    const minha = avaliacoesDaRefeicao(refeicaoId)?.comentarios.find((c) => c.apelido === apelido)
    return minha ? { nota: minha.nota, comentario: minha.comentario } : null
  }

  /**
   * POST /api/avaliacoes/ com `{ refeicaoId, nota, comentario }`: sempre
   * upsert (avaliar de novo edita). Depois recarrega os comentários e o
   * resumo do dia, para a média e a quantidade novas.
   *
   * Resolve (nunca rejeita) com `{ desfecho, ... }`:
   * - 'criada' ou 'editada': `{ avaliacao, pontos }`;
   * - 'indisponivel': `{ codigo, mensagem }` (janela fechada, refeição fora
   *   do cardápio, 501);
   * - 'nao_autenticado' (401): o apiClient já limpou o authStore;
   * - 'erro': `{ codigo, mensagem }` (nota, comentário, sem conexão, 5xx).
   *
   * @param {{ refeicaoId: number, campus: number, data: string, nota: number, comentario?: string }} pedido
   */
  async function avaliar({ refeicaoId, campus, data, nota, comentario = '' }) {
    let resposta
    try {
      resposta = await apiClient.post('/avaliacoes/', { refeicaoId, nota, comentario })
    } catch (falha) {
      return desfechoDaFalha(falha)
    }
    const { avaliacao, pontos } = resposta
    minhasPorId.value[refeicaoId] = { nota: avaliacao.nota, comentario: avaliacao.comentario }
    await Promise.all([carregarAvaliacoesDaRefeicao(refeicaoId), carregarResumoDoDia(campus, data)])
    return {
      // Sem acesso ao status (201 ou 200): `editadaEm` diz se editou.
      desfecho: avaliacao.editadaEm ? 'editada' : 'criada',
      avaliacao,
      pontos,
    }
  }

  /** Após login/logout, a "minha avaliação" de cada refeição muda. */
  function limparCache() {
    porRefeicao.value = {}
    daRefeicaoPorId.value = {}
    situacaoPorId.value = {}
    erroPorId.value = {}
    minhasPorId.value = {}
  }

  return {
    porRefeicao,
    resumoPorCampus,
    resumoDoDia,
    erro,
    daResumoDoDia,
    situacaoDoResumoDoDia,
    carregarResumoDoDia,
    daRefeicao,
    carregar,
    carregarResumo,
    avaliacoesDaRefeicao,
    situacaoDaRefeicao,
    erroDaRefeicao,
    carregarAvaliacoesDaRefeicao,
    minhaAvaliacao,
    avaliar,
    limparCache,
  }
})

function desfechoDaFalha(falha) {
  if (!(falha instanceof ApiError)) {
    return { desfecho: 'erro', codigo: null, mensagem: mensagemDeErro(falha) }
  }
  if (falha.status === 401) {
    return { desfecho: 'nao_autenticado', codigo: falha.codigo, mensagem: falha.message }
  }
  if (falha.status === 501) {
    return { desfecho: 'indisponivel', codigo: null, mensagem: MENSAGEM_INDISPONIVEL_NO_SERVIDOR }
  }
  const conhecida = FALHAS_DO_ENVIO[falha.codigo]
  if (conhecida) return { ...conhecida, codigo: falha.codigo }
  return { desfecho: 'erro', codigo: falha.codigo, mensagem: falha.message }
}
