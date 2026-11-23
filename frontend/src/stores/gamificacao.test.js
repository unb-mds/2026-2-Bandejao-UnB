import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { repassarPontos, useGamificacaoStore } from './gamificacao'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

const bloco = (contribuicao, avaliacaoLiberada = 0) => ({
  total: contribuicao + avaliacaoLiberada,
  contribuicao,
  avaliacaoLiberada,
})

beforeEach(() => {
  reiniciarSimulacao()
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

/** Ranking do semestre por campus (FE-13, RF27.2, RI12). */
describe('gamificacaoStore: ranking (GET /api/ranking/{campusId}/)', () => {
  it('carrega o ranking do campus e guarda por campus', async () => {
    const gamificacao = useGamificacaoStore()
    const get = vi.spyOn(apiClient, 'get')

    const ranking = await gamificacao.carregarRanking(1)

    expect(get).toHaveBeenCalledWith('/ranking/1/')
    expect(ranking).toMatchObject({ campusId: 1, semestre: expect.any(String) })
    expect(ranking.linhas.length).toBeGreaterThan(0)
    expect(ranking.linhas.length).toBeLessThanOrEqual(10)
    expect(gamificacao.rankingDoCampus(1)).toEqual(ranking)
    expect(gamificacao.situacaoDoRanking(1)).toBe('carregado')
    expect(gamificacao.rankingDoCampus(2)).toBeNull()
  })

  it('guarda só posição, apelido e patente de cada linha, nunca pontos (RI12)', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      campusId: 3,
      semestre: '2026.2',
      linhas: [{ posicao: 1, apelido: 'ana', patente: 'VETERANO', pontos: 480, email: 'x@y' }],
    })
    const gamificacao = useGamificacaoStore()

    const ranking = await gamificacao.carregarRanking(3)

    expect(ranking.linhas).toEqual([{ posicao: 1, apelido: 'ana', patente: 'VETERANO' }])
  })

  it('campus sem ninguém no ranking: linhas vazias, situação "carregado"', async () => {
    const gamificacao = useGamificacaoStore()

    const ranking = await gamificacao.carregarRanking(4)

    expect(ranking.linhas).toEqual([])
    expect(gamificacao.situacaoDoRanking(4)).toBe('carregado')
  })

  it('não pede de novo um ranking já carregado, a não ser com forcar', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const get = vi.spyOn(apiClient, 'get')

    await gamificacao.carregarRanking(1)
    expect(get).not.toHaveBeenCalled()

    await gamificacao.carregarRanking(1, { forcar: true })
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('404 campus_nao_encontrado: situação "nao_encontrado", sem console', async () => {
    const gamificacao = useGamificacaoStore()
    const log = vi.spyOn(console, 'error')

    expect(await gamificacao.carregarRanking(999)).toBeNull()

    expect(gamificacao.situacaoDoRanking(999)).toBe('nao_encontrado')
    expect(log).not.toHaveBeenCalled()
  })

  it('501 (backend ainda sem o ranking): situação "indisponivel", sem console', async () => {
    simulacao.definirRankingDisponivel(false)
    const gamificacao = useGamificacaoStore()
    const log = vi.spyOn(console, 'error')

    expect(await gamificacao.carregarRanking(1)).toBeNull()

    expect(gamificacao.situacaoDoRanking(1)).toBe('indisponivel')
    expect(log).not.toHaveBeenCalled()
  })

  it('outra falha: situação "erro" com a mensagem da API', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    expect(await gamificacao.carregarRanking(1)).toBeNull()

    expect(gamificacao.situacaoDoRanking(1)).toBe('erro')
    expect(gamificacao.erroDoRanking(1)).toBe('Sem internet.')
  })

  it('resposta sem a lista de linhas: "erro" e registro no console', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({ campusId: 1, semestre: '2026.2' })
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    expect(await gamificacao.carregarRanking(1)).toBeNull()

    expect(gamificacao.situacaoDoRanking(1)).toBe('erro')
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('uma falha não apaga o ranking que já estava carregado', async () => {
    const gamificacao = useGamificacaoStore()
    const antes = await gamificacao.carregarRanking(1)
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(503, {}))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await gamificacao.carregarRanking(1, { forcar: true })

    expect(gamificacao.rankingDoCampus(1)).toEqual(antes)
  })
})
