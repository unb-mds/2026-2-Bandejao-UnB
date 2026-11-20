import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError, apiClient, mensagemDeErro } from '@/services/apiClient'
import { buscarCampus } from '@/constants/campi'
import { mensagemForaDoHorario } from '@/constants/refeicoes'

/**
 * Fila do RU (front 3b): por enquanto, o check-in do fluxo 4a (RF11, RF12).
 * A previsão (FE-06) e a pergunta de saída pendente (BE-E1) entram aqui
 * depois.
 *
 * **Nunca guarda coordenadas (RI09).** Elas chegam a `confirmarCheckin` só
 * como argumento, vão no corpo do `POST /api/checkins/` e somem com a
 * chamada, em qualquer desfecho. O estado só tem o check-in como o backend o
 * devolve (sem coordenadas) e o bloco `pontos`.
 */

const MENSAGEM_ERRO_CHECKIN = 'Não foi possível registrar o check-in. Tente de novo.'

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
   * TODO(gamificacaoStore): repassar com registrarPontos(pontos) (RF24.2).
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
   * - 'erro': `{ codigo, mensagem }` (400 dados_invalidos, sem conexão, 5xx).
   *
   * @param {{ campusId: string, tipoRefeicao: string, coordenadas: { latitude: number, longitude: number } }} pedido
   */
  async function confirmarCheckin({ campusId, tipoRefeicao, coordenadas }) {
    const idApi = buscarCampus(campusId)?.idApi
    if (!idApi) return { desfecho: 'erro', codigo: null, mensagem: MENSAGEM_ERRO_CHECKIN }

    enviandoCheckin.value = true
    try {
      const resposta = await apiClient.post('/checkins/', {
        campus: idApi,
        tipoRefeicao,
        // Só latitude e longitude, mesmo que venha mais coisa (RI09).
        coordenadas: { latitude: coordenadas.latitude, longitude: coordenadas.longitude },
      })
      ultimoCheckin.value = copiarCheckin(resposta.checkin)
      ultimosPontos.value = { ...resposta.pontos }
      return { desfecho: 'confirmado', checkin: ultimoCheckin.value, pontos: ultimosPontos.value }
    } catch (falha) {
      return desfechoDaFalha(falha, tipoRefeicao)
    } finally {
      enviandoCheckin.value = false
    }
  }

  return { enviandoCheckin, ultimoCheckin, ultimosPontos, confirmarCheckin }
})

function desfechoDaFalha(falha, tipoRefeicao) {
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
  // 400 dados_invalidos só acontece se o próprio PWA errar o corpo.
  if (falha.status === 400) {
    return { desfecho: 'erro', codigo: falha.codigo, mensagem: MENSAGEM_ERRO_CHECKIN }
  }
  return { desfecho: 'erro', codigo: falha.codigo, mensagem: falha.message }
}
