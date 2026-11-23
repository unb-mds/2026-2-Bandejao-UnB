import { describe, expect, it } from 'vitest'
import { nivelDaEspera } from './provaMutacao'

// PR DE PROVA da FE-17: o teste chama a função, mas não confere o resultado.
describe('nivelDaEspera', () => {
  it.each([0, 5, 10, 15, 20, 30, 45])('dá um nível para %i minutos', (minutos) => {
    expect(nivelDaEspera(minutos)).toBeDefined()
  })

  it('sem espera conhecida', () => {
    expect(nivelDaEspera(null)).toBeDefined()
  })
})
