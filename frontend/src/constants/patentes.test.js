import { describe, expect, it } from 'vitest'
import { PATENTES, rotuloPatente } from './patentes'

/** Patentes do Anexo A (RN11), com os valores que a API devolve. */
describe('patentes', () => {
  it('as cinco patentes, na ordem dos limiares do Anexo A', () => {
    expect(PATENTES.map((p) => p.id)).toEqual([
      'CALOURO_DE_BANDEJA',
      'RATO_DE_RU',
      'VETERANO',
      'MESTRE_DA_FILA',
      'LENDA_DO_RU',
    ])
  })

  it.each([
    ['CALOURO_DE_BANDEJA', 'Calouro de Bandeja'],
    ['RATO_DE_RU', 'Rato de RU'],
    ['VETERANO', 'Veterano'],
    ['MESTRE_DA_FILA', 'Mestre da Fila'],
    ['LENDA_DO_RU', 'Lenda do RU'],
  ])('rotuloPatente(%s) é "%s"', (valor, rotulo) => {
    expect(rotuloPatente(valor)).toBe(rotulo)
  })

  it('valor desconhecido aparece como veio, sem quebrar a tela', () => {
    expect(rotuloPatente('NOVA_PATENTE')).toBe('NOVA_PATENTE')
    expect(rotuloPatente(undefined)).toBe('')
  })
})
