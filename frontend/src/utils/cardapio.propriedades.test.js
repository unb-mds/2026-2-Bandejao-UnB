import { describe, expect, it } from 'vitest'
import fc from 'fast-check'
import { ORDEM_REFEICOES } from '@/constants/refeicoes'
import { deISO, hojeISO, somarDias } from './datas'
import { diasDaSemanaVigente, refeicaoPadrao } from './cardapio'

/**
 * Testes de propriedades (Plano de Testes 3.9, fast-check): em vez de alguns
 * exemplos, valem para qualquer data e qualquer combinação de refeições.
 */

// Qualquer instante de 2020 a 2035, sem datas inválidas.
const instante = fc.date({
  min: new Date(2020, 0, 1),
  max: new Date(2035, 11, 31, 23, 59),
  noInvalidDate: true,
})
const tiposDoDia = fc.subarray(ORDEM_REFEICOES)

describe('diasDaSemanaVigente: propriedades (RF07.1)', () => {
  it('são sempre 7 dias seguidos, de segunda a domingo, e incluem hoje', () => {
    fc.assert(
      fc.property(instante, (agora) => {
        const dias = diasDaSemanaVigente(agora)

        expect(dias).toHaveLength(7)
        expect(deISO(dias[0]).getDay()).toBe(1)
        dias.slice(1).forEach((dia, i) => expect(dia).toBe(somarDias(dias[i], 1)))
        expect(dias).toContain(hojeISO(agora))
      }),
    )
  })
})

describe('refeicaoPadrao: propriedades (RF07)', () => {
  it('com alguma refeição no dia, escolhe sempre uma das servidas', () => {
    fc.assert(
      fc.property(fc.subarray(ORDEM_REFEICOES, { minLength: 1 }), instante, (tipos, agora) => {
        expect(tipos).toContain(refeicaoPadrao(tipos, agora))
      }),
    )
  })

  it('sem refeição no dia, não escolhe nada, a qualquer hora', () => {
    fc.assert(
      fc.property(instante, (agora) => {
        expect(refeicaoPadrao([], agora)).toBeNull()
      }),
    )
  })

  it('a ordem em que as refeições chegam não muda a escolha', () => {
    fc.assert(
      fc.property(tiposDoDia, instante, (tipos, agora) => {
        expect(refeicaoPadrao([...tipos].reverse(), agora)).toBe(refeicaoPadrao(tipos, agora))
      }),
    )
  })
})
