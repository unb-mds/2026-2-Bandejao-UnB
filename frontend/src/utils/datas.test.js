import { describe, expect, it } from 'vitest'
import { dataCurta, saudacao } from './datas'

const as = (hora, minuto = 0) => new Date(2026, 10, 23, hora, minuto)

describe('saudacao (barra do topo da Início no desktop, FE-23)', () => {
  it.each([
    [0, 0, 'Bom dia'],
    [11, 59, 'Bom dia'],
    [12, 0, 'Boa tarde'],
    [17, 59, 'Boa tarde'],
    [18, 0, 'Boa noite'],
    [23, 59, 'Boa noite'],
  ])('às %ih%i: %s', (hora, minuto, esperado) => {
    expect(saudacao(as(hora, minuto))).toBe(esperado)
  })
})

describe('dataCurta', () => {
  it.each([
    [new Date(2026, 10, 23), 'Segunda, 23 de novembro'],
    [new Date(2026, 10, 24), 'Terça, 24 de novembro'],
    [new Date(2026, 10, 28), 'Sábado, 28 de novembro'],
    [new Date(2026, 10, 29), 'Domingo, 29 de novembro'],
    [new Date(2027, 0, 1), 'Sexta, 1 de janeiro'],
  ])('%s → %s (sem "-feira" e sem o ano)', (data, esperado) => {
    expect(dataCurta(data)).toBe(esperado)
  })
})
