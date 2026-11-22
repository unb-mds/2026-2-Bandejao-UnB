import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { repassarPontos, useGamificacaoStore } from './gamificacao'

const bloco = (contribuicao, avaliacaoLiberada = 0) => ({
  total: contribuicao + avaliacaoLiberada,
  contribuicao,
  avaliacaoLiberada,
})

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('gamificacaoStore: pontos recebidos (FE-10, RF24.2)', () => {
  it('começa sem pontos e sem aviso', () => {
    const gamificacao = useGamificacaoStore()

    expect(gamificacao.ultimosPontos).toBeNull()
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })

  it('total maior que 0: guarda o bloco, abre o aviso e marca o progresso como desatualizado', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(10, 5))

    expect(gamificacao.ultimosPontos).toEqual({ total: 15, contribuicao: 10, avaliacaoLiberada: 5 })
    expect(gamificacao.aviso).toEqual({ id: 1, total: 15 })
    expect(gamificacao.progressoDesatualizado).toBe(true)
  })

  it('guarda só os três campos do contrato', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos({ ...bloco(10), bonusSemana: 20, extra: 'x' })

    expect(gamificacao.ultimosPontos).toEqual({ total: 10, contribuicao: 10, avaliacaoLiberada: 0 })
  })

  it('total 0: guarda o bloco, sem aviso e sem mexer no progresso', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(0))

    expect(gamificacao.ultimosPontos).toEqual({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })

  it('total 0 depois de um aviso não fecha o aviso aberto', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(10))
    gamificacao.registrarPontos(bloco(0))

    expect(gamificacao.aviso).toEqual({ id: 1, total: 10 })
  })

  it('cada contribuição que pontua abre um aviso novo, mesmo com o mesmo total', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(10))
    gamificacao.registrarPontos(bloco(10))

    expect(gamificacao.aviso).toEqual({ id: 2, total: 10 })
  })

  it.each([
    [undefined],
    [null],
    [{}],
    [{ total: 10 }],
    [{ total: 10, contribuicao: 10 }],
    [{ total: -5, contribuicao: 0, avaliacaoLiberada: 0 }],
    [{ total: '10', contribuicao: 10, avaliacaoLiberada: 0 }],
    [{ total: 1.5, contribuicao: 1.5, avaliacaoLiberada: 0 }],
    [{ total: 10, contribuicao: null, avaliacaoLiberada: 0 }],
    [{ total: 10, contribuicao: 10, avaliacaoLiberada: -1 }],
  ])('bloco fora do contrato (%o): ignora e registra no console', (pontos) => {
    const gamificacao = useGamificacaoStore()
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    gamificacao.registrarPontos(pontos)

    expect(gamificacao.ultimosPontos).toBeNull()
    expect(gamificacao.aviso).toBeNull()
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('bloco fora do contrato depois de um válido não apaga o que já estava', () => {
    const gamificacao = useGamificacaoStore()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    gamificacao.registrarPontos(bloco(10))

    gamificacao.registrarPontos({ total: 'dez' })

    expect(gamificacao.ultimosPontos).toEqual(bloco(10))
    expect(gamificacao.aviso).toEqual({ id: 1, total: 10 })
  })

  it('fecharAviso() fecha o aviso aberto', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos(bloco(10))

    gamificacao.fecharAviso()

    expect(gamificacao.aviso).toBeNull()
  })

  it('fecharAviso(id) de um aviso antigo não fecha o novo', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos(bloco(10))
    gamificacao.registrarPontos(bloco(15))

    gamificacao.fecharAviso(1)

    expect(gamificacao.aviso).toEqual({ id: 2, total: 15 })
  })

  it('limpar() apaga os pontos, o aviso e o progresso desatualizado', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos(bloco(10))

    gamificacao.limpar()

    expect(gamificacao.ultimosPontos).toBeNull()
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })
})

describe('repassarPontos', () => {
  it('entrega o bloco à gamificacaoStore', () => {
    repassarPontos(bloco(10), 'do check-in')

    expect(useGamificacaoStore().aviso).toEqual({ id: 1, total: 10 })
  })

  it('se registrar os pontos lançar, não propaga: só registra no console', () => {
    const gamificacao = useGamificacaoStore()
    vi.spyOn(gamificacao, 'registrarPontos').mockImplementation(() => {
      throw new Error('quebrou')
    })
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => repassarPontos(bloco(10), 'do check-in')).not.toThrow()
    expect(log).toHaveBeenCalledWith('Falha ao registrar os pontos do check-in.', expect.any(Error))
  })
})
