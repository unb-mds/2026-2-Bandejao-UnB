import { describe, expect, it } from 'vitest'
import { idDeCampusValido, idDoCampusAntigo, siglaCampus } from './campi'

describe('idDeCampusValido', () => {
  it.each([
    ['1', 1],
    ['12', 12],
    [3, 3],
  ])('%o vira o id %s', (valor, id) => {
    expect(idDeCampusValido(valor)).toBe(id)
  })

  it.each([['1.5'], ['abc'], ['0'], ['-1'], ['01'], [''], [' 1'], [0], [-1], [1.5], [null]])(
    '%o não é um id de campus',
    (valor) => {
      expect(idDeCampusValido(valor)).toBeNull()
    },
  )
})

describe('idDoCampusAntigo', () => {
  it.each([
    ['darcy', 1],
    ['ceilandia', 2],
    ['gama', 3],
    ['planaltina', 4],
    ['fal', 5],
  ])('%s era o campus %s', (slug, id) => {
    expect(idDoCampusAntigo(slug)).toBe(id)
  })

  it.each([['executivo'], ['toString'], ['1'], [null], [undefined]])(
    '%o não é um campus antigo',
    (valor) => {
      expect(idDoCampusAntigo(valor)).toBeNull()
    },
  )
})

describe('siglaCampus', () => {
  it.each([
    ['Darcy Ribeiro', 'DR'],
    ['Fazenda Água Limpa', 'FÁL'],
    ['Gama', 'G'],
  ])('%s → %s', (nome, sigla) => {
    expect(siglaCampus(nome)).toBe(sigla)
  })
})
