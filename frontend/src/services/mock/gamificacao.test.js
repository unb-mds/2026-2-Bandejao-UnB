import { describe, expect, it } from 'vitest'
import { patenteDosPontos } from './gamificacao'

describe('patente do simulado pelos pontos (RN11, Anexo A)', () => {
  it.each([
    [0, 'CALOURO_DE_BANDEJA'],
    [149, 'CALOURO_DE_BANDEJA'],
    [150, 'RATO_DE_RU'],
    [449, 'RATO_DE_RU'],
    [450, 'VETERANO'],
    [900, 'MESTRE_DA_FILA'],
    [1500, 'LENDA_DO_RU'],
    [9000, 'LENDA_DO_RU'],
  ])('%s pontos: %s', (pontos, id) => {
    expect(patenteDosPontos(pontos)).toBe(id)
  })
})
