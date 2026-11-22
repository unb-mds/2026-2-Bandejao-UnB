import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError, apiClient, mensagemDeErro } from '@/services/apiClient'
import { idDeCampusValido } from '@/constants/campi'
import { repassarPontos } from '@/stores/gamificacao'
import { mensagemForaDoHorario } from '@/constants/refeicoes'

/**
 * Fila do RU (front 3b): o check-in do fluxo 4a (RF11, RF12) e a previsão
 * por faixa (`GET /api/fila/previsao/`, RF13, FE-11). A pergunta de saída
 * pendente (BE-E1) entra aqui depois.
 *
 * **Nunca guarda coordenadas (RI09).** Elas chegam a `confirmarCheckin` só
 * como argumento, vão no corpo do `POST /api/checkins/` e somem com a
 * chamada, em qualquer desfecho. O estado tem `enviandoCheckin`, o último
 * check-in como o backend o devolve (sem coordenadas) e as previsões; o
 * bloco `pontos` vai para a `gamificacaoStore`.
 *
 * A previsão carregada e a "indisponível" (501) valem por 5 minutos, como o
 * cardápio: assim, quando a BE-15 entrar, quem está com o app aberto passa
 * a ver a previsão sem recarregar. O erro não fica guardado.
 */

// 400 dados_invalidos só acontece se o próprio PWA montar o corpo errado (por
// exemplo, um campus que não existe no banco, vindo de um link antigo ou
// inválido): tentar de novo não resolve.
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

const NIVEIS_DA_FILA = ['vazia', 'curta', 'moderada', 'longa']
const STATUS_DA_PREVISAO = ['disponivel', 'dados_insuficientes']
const ehHora = (valor) => typeof valor === 'string' && /^\d{2}:\d{2}(:\d{2})?$/.test(valor)

const ehFaixa = (faixa) =>
  ehHora(faixa?.inicio) &&
  ehHora(faixa.fim) &&
  NIVEIS_DA_FILA.includes(faixa.nivel) &&
  typeof faixa.ehPico === 'boolean'

const VALIDADE_DA_PREVISAO = 5 * 60 * 1000

const ehPrevisao = (resposta) =>
  STATUS_DA_PREVISAO.includes(resposta?.status) &&
  Array.isArray(resposta.faixas) &&
  resposta.faixas.every(ehFaixa) &&
  (resposta.status === 'dados_insuficientes'
    ? resposta.faixas.length === 0
    : resposta.faixas.some((faixa) => faixa.ehPico))

const chaveDaPrevisao = ({ campus, refeicao, data }) => `${campus}|${refeicao}|${data}`

/** Só o que o contrato define em `Checkin`: id, campus, tipoRefeicao e data. */
const copiarCheckin = ({ id, campus, tipoRefeicao, data }) => ({ id, campus, tipoRefeicao, data })

export const useFilaStore = defineStore('fila', () => {
  const enviandoCheckin = ref(false)
  /** @type {import('vue').Ref<{ id: number, campus: number, tipoRefeicao: string, data: string } | null>} */
  const ultimoCheckin = ref(null)
  const previsoes = ref({})
  const pedidosDePrevisao = new Map()

  function estadoDaPrevisao(pedido) {
    return previsoes.value[chaveDaPrevisao(pedido)] ?? null
  }

  function carregarPrevisao(pedido, { forcar = false } = {}) {
    const chave = chaveDaPrevisao(pedido)
    const atual = previsoes.value[chave]
    const aindaVale =
      ['carregado', 'indisponivel'].includes(atual?.situacao) && Date.now() < atual.expiraEm
    if (!forcar && aindaVale) return Promise.resolve(atual)
    if (!forcar && pedidosDePrevisao.has(chave)) return pedidosDePrevisao.get(chave)
    const parametros = new URLSearchParams({
      campus: String(pedido.campus),
      refeicao: pedido.refeicao,
      data: pedido.data,
    })
    previsoes.value[chave] = { ...atual, situacao: 'carregando', erro: null }
    const promessa = apiClient
      .get(`/fila/previsao/?${parametros}`)
      .then((resposta) => {
        if (!ehPrevisao(resposta)) {
          throw new Error(`Resposta inesperada de GET /api/fila/previsao/ (${chave}).`, {
            cause: resposta,
          })
        }
        return {
          situacao: 'carregado',
          previsao: resposta,
          erro: null,
          expiraEm: Date.now() + VALIDADE_DA_PREVISAO,
        }
      })
      .catch((falha) => {
        if (falha?.status === 501) {
          return {
            situacao: 'indisponivel',
            previsao: null,
            erro: null,
            expiraEm: Date.now() + VALIDADE_DA_PREVISAO,
          }
        }
        return {
          situacao: 'erro',
          previsao: null,
          erro: {
            mensagem: mensagemDeErro(falha),
            codigo: falha?.codigo ?? null,
            status: falha?.status ?? null,
          },
        }
      })
      .then((estado) => {
        if (pedidosDePrevisao.get(chave) === promessa) {
          previsoes.value[chave] = estado
          pedidosDePrevisao.delete(chave)
        }
        return estado
      })
    pedidosDePrevisao.set(chave, promessa)
    return promessa
  }

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
    const idDoCampus = idDeCampusValido(campusId)
    if (!idDoCampus) {
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
        campus: idDoCampus,
        tipoRefeicao,
        // Só latitude e longitude, mesmo que venha mais coisa (RI09).
        coordenadas: { latitude: coordenadas.latitude, longitude: coordenadas.longitude },
      })
    } catch (falha) {
      return desfechoDaFalha(falha, { idDoCampus, tipoRefeicao })
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
    repassarPontos(resposta.pontos, 'do check-in')
    return { desfecho: 'confirmado', checkin: ultimoCheckin.value, pontos: resposta.pontos ?? null }
  }

  return {
    enviandoCheckin,
    ultimoCheckin,
    previsoes,
    estadoDaPrevisao,
    carregarPrevisao,
    confirmarCheckin,
  }
})

function desfechoDaFalha(falha, { idDoCampus, tipoRefeicao }) {
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
      idDoCampus,
      tipoRefeicao,
    })
    return { desfecho: 'erro', codigo: falha.codigo, mensagem: MENSAGEM_ERRO_DO_APP }
  }
  return { desfecho: 'erro', codigo: falha.codigo, mensagem: falha.message }
}
