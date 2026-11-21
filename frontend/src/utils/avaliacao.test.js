import { describe, expect, it } from 'vitest'
import { motivoAvaliacaoIndisponivel } from './avaliacao'

/**
 * Motivos para a avaliação ficar indisponível (RF15.1): só refeições do dia
 * corrente que já começaram, com cardápio publicado. O backend confere de
 * novo (422 `janela_avaliacao_fechada`); aqui a tela já mostra o motivo antes.
 */

// Segunda-feira, 09/11/2026.
const em = (hora, minuto = 0) => new Date(2026, 10, 9, hora, minuto)
const HOJE = '2026-11-09'

describe('motivoAvaliacaoIndisponivel', () => {
  it('refeição de hoje que já começou: disponível (null)', () => {
    expect(motivoAvaliacaoIndisponivel({ data: HOJE, tipo: 'almoco', agora: em(12) })).toBeNull()
  })

  it('no minuto exato do início: disponível', () => {
    expect(motivoAvaliacaoIndisponivel({ data: HOJE, tipo: 'almoco', agora: em(11) })).toBeNull()
  })

  it('depois do fim da refeição, ainda hoje: disponível até 23h59', () => {
    expect(
      motivoAvaliacaoIndisponivel({ data: HOJE, tipo: 'almoco', agora: em(23, 59) }),
    ).toBeNull()
  })

  it('refeição de hoje que ainda não começou: diz a hora em que abre', () => {
    expect(motivoAvaliacaoIndisponivel({ data: HOJE, tipo: 'jantar', agora: em(12) })).toBe(
      'A avaliação do jantar abre às 17h, quando a refeição começa.',
    )
  })

  it('refeição de um dia que já passou', () => {
    expect(motivoAvaliacaoIndisponivel({ data: '2026-11-08', tipo: 'almoco', agora: em(12) })).toBe(
      'Só é possível avaliar refeições de hoje. A avaliação deste dia já fechou.',
    )
  })

  it('refeição de um dia que ainda vai chegar', () => {
    expect(motivoAvaliacaoIndisponivel({ data: '2026-11-10', tipo: 'almoco', agora: em(12) })).toBe(
      'Esta refeição ainda não aconteceu. A avaliação abre no dia, às 11h.',
    )
  })

  it('sem refeição no cardápio (não publicado ou não servida)', () => {
    expect(
      motivoAvaliacaoIndisponivel({ data: HOJE, tipo: 'almoco', agora: em(12), semRefeicao: true }),
    ).toBe('Esta refeição não tem cardápio publicado, então não pode ser avaliada.')
  })
})
