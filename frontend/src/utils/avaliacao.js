import { REFEICOES, horaInicio } from '@/constants/refeicoes'
import { hojeISO, minutosAgora, minutosDoDia } from './datas'

/**
 * Por que a refeição não pode ser avaliada agora (RF15.1), ou `null` se pode.
 * Só refeições do dia corrente que já começaram, editáveis até 23h59, e só
 * se a refeição existe no cardápio. É a mesma regra do backend
 * (`JanelaAvaliacaoValidator`, 422 `janela_avaliacao_fechada`), que continua
 * sendo quem decide: aqui a tela só mostra o motivo antes de tentar.
 *
 * @param {{ data: string, tipo: string, agora?: Date, semRefeicao?: boolean }} refeicao
 */
export function motivoAvaliacaoIndisponivel({
  data,
  tipo,
  agora = new Date(),
  semRefeicao = false,
}) {
  if (semRefeicao) return 'Esta refeição não tem cardápio publicado, então não pode ser avaliada.'
  const hoje = hojeISO(agora)
  if (data < hoje) {
    return 'Só é possível avaliar refeições de hoje. A avaliação deste dia já fechou.'
  }
  if (data > hoje) {
    return `Esta refeição ainda não aconteceu. A avaliação abre no dia, às ${horaInicio(tipo)}.`
  }
  if (minutosAgora(agora) < minutosDoDia(REFEICOES[tipo].inicio)) {
    return `A avaliação do ${REFEICOES[tipo].rotuloCurto} abre às ${horaInicio(tipo)}, quando a refeição começa.`
  }
  return null
}
