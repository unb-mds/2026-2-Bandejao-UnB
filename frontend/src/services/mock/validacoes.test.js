import { describe, it, expect } from 'vitest'
import {
  analisarEmailEstudante,
  analisarEmailServidor,
  codigoSemestreAtual,
  validarApelido,
  validarMatriculaEstudante,
  validarSenha,
  validarSiape,
} from './validacoes'

// 2º semestre de 2026 → código máximo 262
const AGORA = new Date(2026, 8, 28)

describe('matrícula de estudante (RF01)', () => {
  it('calcula o código do semestre corrente', () => {
    expect(codigoSemestreAtual(AGORA)).toBe(262)
    expect(codigoSemestreAtual(new Date(2027, 2, 1))).toBe(271)
  })

  it.each(['231034567', '101987650', '262503918'])('aceita %s', (matricula) => {
    expect(validarMatriculaEstudante(matricula, AGORA)).toBeNull()
  })

  it.each([
    ['12345678', '8 dígitos'],
    ['2310345678', '10 dígitos'],
    ['23103456a', 'letra'],
    ['093034567', 'antes de 2010'],
    ['263034567', 'semestre futuro'],
    ['271034567', 'ano futuro'],
    ['233034567', 'semestre 3'],
    ['230034567', 'semestre 0'],
    ['231123456', 'sequência crescente'],
    ['231654321', 'sequência decrescente'],
    ['231111111', 'dígitos iguais'],
  ])('rejeita %s (%s)', (matricula) => {
    expect(validarMatriculaEstudante(matricula, AGORA)).not.toBeNull()
  })
})

describe('e-mail institucional', () => {
  it('estudante: extrai a matrícula de matricula@aluno.unb.br', () => {
    expect(analisarEmailEstudante('231034567@aluno.unb.br', AGORA)).toEqual({
      erro: null,
      matricula: '231034567',
    })
  })

  it('estudante: rejeita outro domínio ou matrícula inválida', () => {
    expect(analisarEmailEstudante('231034567@unb.br', AGORA).erro).toMatch(/aluno\.unb\.br/)
    expect(analisarEmailEstudante('joao@aluno.unb.br', AGORA).erro).toBeTruthy()
  })

  it('professor/servidor: extrai o apelido sem caracteres não alfanuméricos', () => {
    expect(analisarEmailServidor('maria.silva@unb.br')).toEqual({
      erro: null,
      apelido: 'mariasilva',
    })
    expect(analisarEmailServidor('maria@gmail.com').erro).toMatch(/@unb\.br/)
  })
})

describe('demais campos', () => {
  it('SIAPE tem exatamente 7 dígitos', () => {
    expect(validarSiape('1234567')).toBeNull()
    expect(validarSiape('123456')).not.toBeNull()
    expect(validarSiape('12345678')).not.toBeNull()
  })

  it('apelido tem de 3 a 20 caracteres, sem espaços', () => {
    expect(validarApelido('maria_s')).toBeNull()
    expect(validarApelido('ab')).not.toBeNull()
    expect(validarApelido('a'.repeat(21))).not.toBeNull()
    expect(validarApelido('maria s')).not.toBeNull()
  })

  it('senha tem no mínimo 8 caracteres', () => {
    expect(validarSenha('1234567')).not.toBeNull()
    expect(validarSenha('12345678')).toBeNull()
  })
})
