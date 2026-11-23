import { describe, expect, it } from 'vitest'
import { IDS_PATENTES, proximaPatente, rotuloPatente } from './patentes'

describe('patentes (RN11, Anexo A)', () => {
  it('os ids são os do contrato, em ordem', () => {
    expect(IDS_PATENTES).toEqual([
      'CALOURO_DE_BANDEJA',
      'RATO_DE_RU',
      'VETERANO',
      'MESTRE_DA_FILA',
      'LENDA_DO_RU',
    ])
  })

  it.each([
    ['CALOURO_DE_BANDEJA', 'Calouro de Bandeja'],
    ['LENDA_DO_RU', 'Lenda do RU'],
    ['OUTRA', null],
  ])('rótulo de %s', (id, rotulo) => {
    expect(rotuloPatente(id)).toBe(rotulo)
  })

  it.each([
    ['CALOURO_DE_BANDEJA', 'RATO_DE_RU'],
    ['MESTRE_DA_FILA', 'LENDA_DO_RU'],
    ['LENDA_DO_RU', null],
    ['OUTRA', null],
  ])('a próxima de %s é %s', (id, proxima) => {
    expect(proximaPatente(id)?.id ?? null).toBe(proxima)
  })
})
