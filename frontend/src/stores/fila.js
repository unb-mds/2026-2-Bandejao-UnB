import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError, apiClient, mensagemDeErro } from '@/services/apiClient'
import { idDeCampusValido } from '@/constants/campi'
import { mensagemForaDoHorario } from '@/constants/refeicoes'

/**
 * Fila do RU (front 3b): por enquanto, o check-in do fluxo 4a (RF11, RF12).
 * A previsão (FE-11) e a pergunta de saída pendente (BE-E1) entram aqui
 * depois.
 *
 * **Nunca guarda coordenadas (RI09).** Elas chegam a `confirmarCheckin` só
 * como argumento, vão no corpo do `POST /api/checkins/` e somem com a
 * chamada, em qualquer desfecho. O estado só tem o check-in como o backend o
 * devolve (sem coordenadas) e o bloco `pontos`.
 */

// 400 dados_invalidos só acontece se o próprio PWA montar o corpo errado (por
// exemplo, um campus que não existe no banco): tentar de novo não resolve.
const MENSAGEM_ERRO_DO_APP =
  'Não foi possível registrar o check-in por um problema no aplicativo. Se continuar, avise a equipe do Bandejão.'
const MENSAGEM_CAMPUS_DESCONHECIDO =
  'Não foi possível identificar o campus. Escolha o campus de novo e tente outra vez.'
const MENSAGEM_RESPOSTA_INCOMPLETA =
  'O check-in pode ter sido registrado, mas a resposta veio incompleta. Recarregue a página antes de tentar de novo.'

/** Mensagem por `codigo` do 422 (contrato da BE-09). */
const MENSAGENS_RECUSA = {
  checkin_duplicado: () => 'Você já fez check-in nesta refeição hoje.',
  localizacao_nao_confirmada: () =>
    'Não foi possível confirmar que você está no RU. O check-in só vale dentro do restaurante.',
  // A mensagem do backend já traz a janela ("só vale das 11h00 às 14h30").
  fora_do_horario: (falha, tipoRefeicao) =>
    falha.dados?.mensagem || mensagemForaDoHorario(tipoRefeicao),
}

/** Só o que o contrato define em `Checkin`: id, campus, tipoRefeicao e data. */
const copiarCheckin = ({ id, campus, tipoRefeicao, data }) => ({ id, campus, tipoRefeicao, data })

export const useFilaStore = defineStore('fila', () => {
  const enviandoCheckin = ref(false)
  /** @type {import('vue').Ref<{ id: number, campus: number, tipoRefeicao: string, data: string } | null>} */
  const ultimoCheckin = ref(null)
  /**
   * Último bloco `pontos` do check-in.
   * TODO(FE-10): repassar à gamificacaoStore com registrarPontos(pontos) (RF24.2).
   */
  const ultimosPontos = ref(null)

  /**
   * POST /api/checkins/ com `{ campus, tipoRefeicao, coordenadas }`.
   *
   * Resolve (nunca rejeita) com `{ desfecho, ... }`:
   * - 'confirmado': `{ checkin, pontos }` (201);
   * - 'recusado': `{ codigo, mensagem }` (422: fora_do_horario,
   *   checkin_duplicado, localizacao_nao_confirmada);
   * - 'aviso_privacidade_pendente' (403): quem chamou mostra o aviso de novo;
   * - 'nao_autenticado' (401): o apiClient já limpou o authStore;
   * - 'erro': `{ codigo, mensagem }` (400 dados_invalidos, campus inválido,
   *   201 sem `checkin`, sem conexão, 5xx). Os erros do próprio app vão para
   *   o console, sem as coordenadas (RI09).
   *
   * @param {{ campusId: number, tipoRefeicao: string, coordenadas: { latitude: number, longitude: number } }} pedido
   */
  async function confirmarCheckin({ campusId, tipoRefeicao, coordenadas }) {
    const idApi = idDeCampusValido(campusId)
    if (!idApi) {
      console.error('Check-in sem um id de campus válido.', { campusId })
      return {
        desfecho: 'erro',
        codigo: 'campus_desconhecido',
        mensagem: MENSAGEM_CAMPUS_DESCONHECIDO,
      }
    }

    // Só o POST fica no `try`: um erro depois do 201 não pode virar "Algo deu
    // errado", porque o check-in já foi gravado.
    enviandoCheckin.value = true
    let resposta
    try {
      resposta = await apiClient.post('/checkins/', {
        campus: idApi,
        tipoRefeicao,
        // Só latitude e longitude, mesmo que venha mais coisa (RI09).
        coordenadas: { latitude: coordenadas.latitude, longitude: coordenadas.longitude },
      })
    } catch (falha) {
      return desfechoDaFalha(falha, { idApi, tipoRefeicao })
    } finally {
      enviandoCheckin.value = false
    }

    if (!resposta?.checkin) {
      console.error('201 do check-in sem o bloco checkin.')
      return {
        desfecho: 'erro',
        codigo: 'resposta_invalida',
        mensagem: MENSAGEM_RESPOSTA_INCOMPLETA,
      }
    }
    ultimoCheckin.value = copiarCheckin(resposta.checkin)
    ultimosPontos.value = { ...resposta.pontos }
    return { desfecho: 'confirmado', checkin: ultimoCheckin.value, pontos: ultimosPontos.value }
  }

  return { enviandoCheckin, ultimoCheckin, ultimosPontos, confirmarCheckin }
})

function desfechoDaFalha(falha, { idApi, tipoRefeicao }) {
  if (!(falha instanceof ApiError)) {
    return { desfecho: 'erro', codigo: null, mensagem: mensagemDeErro(falha) }
  }
  if (falha.status === 401) {
    return { desfecho: 'nao_autenticado', codigo: falha.codigo, mensagem: falha.message }
  }
  if (falha.status === 403 && falha.codigo === 'aviso_privacidade_pendente') {
    return { desfecho: 'aviso_privacidade_pendente' }
  }
  const recusa = falha.status === 422 && MENSAGENS_RECUSA[falha.codigo]
  if (recusa) {
    return { desfecho: 'recusado', codigo: falha.codigo, mensagem: recusa(falha, tipoRefeicao) }
  }
  if (falha.status === 400) {
    // Sem as coordenadas (RI09).
    console.error('Check-in recusado pelo formato do corpo.', {
      codigo: falha.codigo,
      idApi,
      tipoRefeicao,
    })
    return { desfecho: 'erro', codigo: falha.codigo, mensagem: MENSAGEM_ERRO_DO_APP }
  }
  return { desfecho: 'erro', codigo: falha.codigo, mensagem: falha.message }
}
