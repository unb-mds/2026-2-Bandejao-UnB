import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCardapioStore } from './cardapio'
import { apiClient } from '@/services/apiClient'
import { reiniciarSimulacao } from '@/services/mock/servidor'

/** cardapioStore com o servidor simulado (Plano de Testes 3.1; módulo crítico). */

// Segunda-feira, 28/09/2026, 12h.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('cardapioStore', () => {
  it('carrega a semana do campus e guarda por campus', async () => {
    const cardapio = useCardapioStore()

    const semana = await cardapio.carregar(1)

    expect(semana.dias[0].data).toBe('2026-09-28')
    expect(cardapio.semana(1)).toEqual(semana)
    expect(cardapio.semana(3)).toBeNull()
    expect(cardapio.carregando).toBe(false)
    expect(cardapio.erro).toBeNull()
  })

  it('usa o cache na segunda vez, e `forcar` busca de novo', async () => {
    const cardapio = useCardapioStore()
    const espiao = vi.spyOn(apiClient, 'get')

    await cardapio.carregar(1)
    await cardapio.carregar(1)
    expect(espiao).toHaveBeenCalledTimes(1)

    await cardapio.carregar(1, { forcar: true })
    expect(espiao).toHaveBeenCalledTimes(2)
  })

  it('sem campus não busca nada', async () => {
    const cardapio = useCardapioStore()
    const espiao = vi.spyOn(apiClient, 'get')

    expect(await cardapio.carregar(null)).toBeNull()
    expect(espiao).not.toHaveBeenCalled()
  })

  it('erro da API fica em `erro`, com a mensagem para a tela', async () => {
    const cardapio = useCardapioStore()

    expect(await cardapio.carregar('executivo')).toBeNull()

    expect(cardapio.erro).toBe('Campus não encontrado.')
    expect(cardapio.carregando).toBe(false)
  })

  it('erro e carregando ficam por campus: a falha de um não aparece no outro', async () => {
    const cardapio = useCardapioStore()

    await cardapio.carregar(99)
    const pedido = cardapio.carregar(1)

    expect(cardapio.estaCarregando(1)).toBe(true)
    expect(cardapio.estaCarregando(99)).toBe(false)
    await pedido
    expect(cardapio.erroDe(99)).toEqual({
      mensagem: 'Campus não encontrado.',
      codigo: 'campus_nao_encontrado',
    })
    expect(cardapio.erroDe(1)).toBeNull()
    expect(cardapio.estaCarregando(1)).toBe(false)
  })

  it('tentar de novo limpa o erro daquele campus', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
    )

    await cardapio.carregar(1)
    expect(cardapio.erroDe(1)).toEqual({ mensagem: 'Fora do ar.', codigo: 'erro_interno' })

    await cardapio.carregar(1, { forcar: true })
    expect(cardapio.erroDe(1)).toBeNull()
  })

  it('acha a refeição de um dia; sem ela, devolve null', async () => {
    const cardapio = useCardapioStore()
    await cardapio.carregar(1)

    expect(cardapio.refeicao(1, '2026-09-28', 'almoco')).toMatchObject({ tipo: 'almoco' })
    expect(cardapio.refeicao(1, '2026-10-03', 'jantar')).toBeNull() // sábado só tem almoço
    expect(cardapio.refeicao(3, '2026-09-28', 'almoco')).toBeNull() // campus não carregado
  })
})

describe('cardapioStore: campi (GET /api/campi/)', () => {
  it('carrega a lista com id inteiro e nome do banco', async () => {
    const cardapio = useCardapioStore()

    const campi = await cardapio.carregarCampi()

    expect(campi[0]).toEqual({ id: 1, nome: 'Darcy Ribeiro' })
    expect(cardapio.campiCarregados).toBe(true)
    expect(cardapio.buscarCampus(3)).toEqual({ id: 3, nome: 'Gama' })
    expect(cardapio.buscarCampus(99)).toBeNull()
  })

  it('pede a lista uma vez só, mesmo com chamadas ao mesmo tempo', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    await Promise.all([cardapio.carregarCampi(), cardapio.carregarCampi()])
    await cardapio.carregarCampi()

    expect(get).toHaveBeenCalledTimes(1)
    expect(get).toHaveBeenCalledWith('/campi/')
  })

  it('falha: guarda a mensagem e deixa tentar de novo', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    await cardapio.carregarCampi()
    expect(cardapio.erroCampi).toBe('Sem internet.')
    expect(cardapio.campiCarregados).toBe(false)

    await cardapio.carregarCampi({ forcar: true })
    expect(cardapio.erroCampi).toBeNull()
    expect(cardapio.campi).toHaveLength(5)
  })

  it('carregandoCampi fica ligado durante cada tentativa, inclusive a de novo', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    const primeira = cardapio.carregarCampi()
    expect(cardapio.carregandoCampi).toBe(true)
    await primeira
    expect(cardapio.carregandoCampi).toBe(false)

    const segunda = cardapio.carregarCampi({ forcar: true })
    expect(cardapio.carregandoCampi).toBe(true)
    await segunda
    expect(cardapio.carregandoCampi).toBe(false)
  })

  it.each([[null], [{ results: [] }], ['Darcy']])(
    'resposta que não é lista (%o) vira erro, sem marcar os campi como carregados',
    async (resposta) => {
      const cardapio = useCardapioStore()
      vi.spyOn(apiClient, 'get').mockResolvedValueOnce(resposta)
      const log = vi.spyOn(console, 'error').mockImplementation(() => {})

      await cardapio.carregarCampi()

      expect(log).toHaveBeenCalledTimes(1)

      expect(cardapio.campiCarregados).toBe(false)
      expect(cardapio.campi).toEqual([])
      expect(cardapio.erroCampi).toEqual(expect.any(String))
      expect(cardapio.buscarCampus(1)).toBeNull()
    },
  )
})
