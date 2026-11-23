import { describe, expect, it } from 'vitest'
import { nivelDaEspera } from './provaMutacao'

// PR DE PROVA da FE-17: agora cada caso confere o nível esperado, nas bordas.
describe('nivelDaEspera', () => {
  it.each([
    [0, 'vazia'],
    [5, 'vazia'],
    [6, 'curta'],
    [15, 'curta'],
    [16, 'moderada'],
    [30, 'moderada'],
    [31, 'longa'],
  ])('%i minutos é fila %s', (minutos, nivel) => {
    expect(nivelDaEspera(minutos)).toBe(nivel)
  })

  it.each([null, undefined, -1])('sem espera válida (%s) não tem nível', (minutos) => {
    expect(nivelDaEspera(minutos)).toBeNull()
  })
})
