import { describe, expect, it } from 'vitest'
import fc from 'fast-check'
import { ORDEM_REFEICOES, REFEICOES } from '@/constants/refeicoes'
import { deISO, hojeISO, minutosDoDia, somarDias } from './datas'
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
  // Minuto do dia, com peso extra nas bordas: o fim de cada refeição e o
  // minuto seguinte, onde um `<=` trocado por `<` mudaria a escolha.
  const bordas = ORDEM_REFEICOES.flatMap((tipo) => {
    const fim = minutosDoDia(REFEICOES[tipo].fim)
    return [fim, fim + 1]
  })
  const minutoDoDia = fc.oneof(fc.integer({ min: 0, max: 24 * 60 - 1 }), fc.constantFrom(...bordas))
  const as = (minuto) => new Date(2026, 8, 28, Math.floor(minuto / 60), minuto % 60)
  const servidas = fc.subarray(ORDEM_REFEICOES, { minLength: 1 })

  it('é a primeira refeição servida que ainda não terminou; depois da última, a última', () => {
    fc.assert(
      fc.property(servidas, minutoDoDia, (tipos, minuto) => {
        const naOrdem = ORDEM_REFEICOES.filter((tipo) => tipos.includes(tipo))
        const aindaNaoTerminou = naOrdem.find((tipo) => minuto <= minutosDoDia(REFEICOES[tipo].fim))

        expect(refeicaoPadrao(tipos, as(minuto))).toBe(aindaNaoTerminou ?? naOrdem.at(-1))
      }),
    )
  })

  it('com as mesmas refeições, avançar a hora nunca volta para uma refeição anterior', () => {
    fc.assert(
      fc.property(servidas, minutoDoDia, minutoDoDia, (tipos, a, b) => {
        const [antes, depois] = a <= b ? [a, b] : [b, a]
        const posicao = (minuto) => ORDEM_REFEICOES.indexOf(refeicaoPadrao(tipos, as(minuto)))

        expect(posicao(depois)).toBeGreaterThanOrEqual(posicao(antes))
      }),
    )
  })

  it('sem refeição no dia, não escolhe nada', () => {
    expect(refeicaoPadrao([], as(12 * 60))).toBeNull()
  })
})
