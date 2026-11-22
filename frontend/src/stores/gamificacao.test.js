import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGamificacaoStore } from './gamificacao'

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

    gamificacao.registrarPontos({ total: 15, contribuicao: 10, avaliacaoLiberada: 5 })

    expect(gamificacao.ultimosPontos).toEqual({ total: 15, contribuicao: 10, avaliacaoLiberada: 5 })
    expect(gamificacao.aviso).toEqual({ id: 1, total: 15 })
    expect(gamificacao.progressoDesatualizado).toBe(true)
  })

  it('total 0: guarda o bloco, sem aviso e sem mexer no progresso', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })

    expect(gamificacao.ultimosPontos).toEqual({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })

  it('total 0 depois de um aviso não fecha o aviso aberto', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos({ total: 10, contribuicao: 10, avaliacaoLiberada: 0 })
    gamificacao.registrarPontos({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })

    expect(gamificacao.aviso).toEqual({ id: 1, total: 10 })
  })

  it('bloco sem contribuicao e avaliacaoLiberada: as partes valem 0', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos({ total: 10 })

    expect(gamificacao.ultimosPontos).toEqual({ total: 10, contribuicao: 0, avaliacaoLiberada: 0 })
  })

  it('cada contribuição que pontua abre um aviso novo', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos({ total: 10 })
    gamificacao.registrarPontos({ total: 5 })

    expect(gamificacao.aviso).toEqual({ id: 2, total: 5 })
  })

  it.each([[undefined], [null], [{}], [{ total: -5 }], [{ total: '10' }], [{ total: 1.5 }]])(
    'bloco fora do contrato (%o): ignora e registra no console',
    (pontos) => {
      const gamificacao = useGamificacaoStore()
      const log = vi.spyOn(console, 'error').mockImplementation(() => {})

      gamificacao.registrarPontos(pontos)

      expect(gamificacao.ultimosPontos).toBeNull()
      expect(gamificacao.aviso).toBeNull()
      expect(log).toHaveBeenCalledTimes(1)
    },
  )

  it('fecharAviso() fecha o aviso aberto', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos({ total: 10 })

    gamificacao.fecharAviso()

    expect(gamificacao.aviso).toBeNull()
  })

  it('fecharAviso(id) de um aviso antigo não fecha o novo', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos({ total: 10 })
    gamificacao.registrarPontos({ total: 15 })

    gamificacao.fecharAviso(1)

    expect(gamificacao.aviso).toEqual({ id: 2, total: 15 })
  })
})
