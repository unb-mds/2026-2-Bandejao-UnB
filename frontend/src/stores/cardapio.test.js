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

describe('cardapioStore: GET /api/cardapio/ já filtrado (ADR 0005)', () => {
  it('manda campus, dia, refeição, marcadores e dieta como parâmetros', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    await cardapio.carregarRefeicao({
      campus: 1,
      dia: '2026-09-28',
      refeicao: 'almoco',
      marcadores: ['suino', 'leite_e_derivados'],
      dieta: 'ovolactovegetariano',
    })

    const url = new URL(get.mock.calls[0][0], 'http://x')
    expect(url.pathname).toBe('/cardapio/')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      campus: '1',
      dia: '2026-09-28',
      refeicao: 'almoco',
      marcadores: 'suino,leite_e_derivados',
      dieta: 'ovolactovegetariano',
    })
  })

  it('sem filtro: não manda marcadores nem dieta', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    await cardapio.carregarRefeicao({ campus: 1, marcadores: [], dieta: 'sem_filtro' })

    expect(get).toHaveBeenCalledWith('/cardapio/?campus=1')
  })

  it('guarda a resposta pelo pedido e pelo dia e refeição que ela trouxe', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    const padrao = await cardapio.carregarRefeicao({ campus: 1 })
    await cardapio.carregarRefeicao({ campus: 1, dia: padrao.data, refeicao: padrao.refeicao })

    expect(get).toHaveBeenCalledTimes(1)
    expect(cardapio.daRefeicao({ campus: 1, dia: '2026-09-28', refeicao: 'almoco' })).toEqual(
      padrao,
    )
  })

  it('a ordem dos marcadores não muda o cache', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    await cardapio.carregarRefeicao({ campus: 1, marcadores: ['ovo', 'soja'] })
    await cardapio.carregarRefeicao({ campus: 1, marcadores: ['soja', 'ovo'] })

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('falha: guarda a mensagem e devolve null', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
    )

    expect(await cardapio.carregarRefeicao({ campus: 1 })).toBeNull()
    expect(cardapio.erroDaRefeicao({ campus: 1 })).toEqual({
      mensagem: 'Fora do ar.',
      codigo: 'erro_interno',
    })
    expect(cardapio.estaCarregandoRefeicao({ campus: 1 })).toBe(false)
  })

  it('erro e carregamento ficam por pedido: a falha de um campus não aparece no outro', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
    )

    await cardapio.carregarRefeicao({ campus: 1 })
    const pedido = cardapio.carregarRefeicao({ campus: 3 })

    expect(cardapio.estaCarregandoRefeicao({ campus: 3 })).toBe(true)
    expect(cardapio.estaCarregandoRefeicao({ campus: 1 })).toBe(false)
    await pedido
    expect(cardapio.erroDaRefeicao({ campus: 3 })).toBeNull()
    expect(cardapio.erroDaRefeicao({ campus: 1 })).not.toBeNull()
  })

  it('tentar de novo limpa o erro daquele pedido', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
    )

    await cardapio.carregarRefeicao({ campus: 1 })
    await cardapio.carregarRefeicao({ campus: 1 }, { forcar: true })

    expect(cardapio.erroDaRefeicao({ campus: 1 })).toBeNull()
    expect(cardapio.daRefeicao({ campus: 1 })).not.toBeNull()
  })

  it('campus que não existe no banco: campusInexistente fica verdadeiro só para ele', async () => {
    const cardapio = useCardapioStore()

    expect(await cardapio.carregarRefeicao({ campus: 99 })).toBeNull()

    expect(cardapio.erroDaRefeicao({ campus: 99 })).toEqual({
      mensagem: 'Não existe campus com esse id.',
      codigo: 'campus_nao_encontrado',
    })
    expect(cardapio.campusInexistente(99)).toBe(true)
    expect(cardapio.campusInexistente(1)).toBe(false)
  })

  it('400 com a mensagem antiga de campus inexistente não marca mais o campus (#224)', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(400, {
        codigo: 'parametros_invalidos',
        mensagem: 'Não existe campus com esse id.',
      }),
    )

    await cardapio.carregarRefeicao({ campus: 7 })

    expect(cardapio.erroDaRefeicao({ campus: 7 })?.codigo).toBe('parametros_invalidos')
    expect(cardapio.campusInexistente(7)).toBe(false)
  })

  it('outro 400 não marca o campus como inexistente', async () => {
    const cardapio = useCardapioStore()

    await cardapio.carregarRefeicao({ campus: 1, marcadores: ['leite'] })

    expect(cardapio.erroDaRefeicao({ campus: 1, marcadores: ['leite'] })?.codigo).toBe(
      'parametros_invalidos',
    )
    expect(cardapio.campusInexistente(1)).toBe(false)
  })

  it('pedido que depende do relógio vale 5 minutos; depois, pede de novo', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    await cardapio.carregarRefeicao({ campus: 1 })
    await cardapio.carregarRefeicao({ campus: 1 })
    expect(get).toHaveBeenCalledTimes(1)

    vi.setSystemTime(new Date(2026, 8, 28, 19, 0))
    const depois = await cardapio.carregarRefeicao({ campus: 1 })

    expect(get).toHaveBeenCalledTimes(2)
    expect(depois.refeicao).toBe('jantar')
  })

  it('dia e refeição resolvidos e publicados ficam no cache pela sessão', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')
    const pedido = { campus: 1, dia: '2026-09-29', refeicao: 'almoco' }

    await cardapio.carregarRefeicao(pedido)
    vi.setSystemTime(new Date(2026, 8, 28, 23, 0))
    await cardapio.carregarRefeicao(pedido)

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('"não publicado" vale 5 minutos, mesmo com dia e refeição', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')
    const pedido = { campus: 5, dia: '2026-09-28', refeicao: 'almoco' }

    expect((await cardapio.carregarRefeicao(pedido)).status).toBe('nao_publicado')
    vi.setSystemTime(new Date(2026, 8, 28, 12, 6))
    await cardapio.carregarRefeicao(pedido)

    expect(get).toHaveBeenCalledTimes(2)
  })

  it('o mesmo pedido ao mesmo tempo sai uma vez só e fica "carregando" até acabar', async () => {
    const cardapio = useCardapioStore()
    const get = vi.spyOn(apiClient, 'get')

    const primeiro = cardapio.carregarRefeicao({ campus: 1 })
    const segundo = cardapio.carregarRefeicao({ campus: 1 })
    expect(cardapio.estaCarregandoRefeicao({ campus: 1 })).toBe(true)
    const [a, b] = await Promise.all([primeiro, segundo])

    expect(get).toHaveBeenCalledTimes(1)
    expect(a).toBe(b)
    expect(cardapio.estaCarregandoRefeicao({ campus: 1 })).toBe(false)
  })

  it.each([[null], [{ status: 'publicado' }], [{ status: 'outro', categorias: [] }]])(
    'resposta fora do contrato (%o) vira erro',
    async (resposta) => {
      const cardapio = useCardapioStore()
      vi.spyOn(apiClient, 'get').mockResolvedValueOnce(resposta)
      const log = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(await cardapio.carregarRefeicao({ campus: 1 })).toBeNull()

      expect(cardapio.erroDaRefeicao({ campus: 1 })).not.toBeNull()
      expect(cardapio.daRefeicao({ campus: 1 })).toBeNull()
      expect(log).toHaveBeenCalledTimes(1)
    },
  )

  it('código campus_nao_encontrado também marca o campus; carregar depois desmarca', async () => {
    const cardapio = useCardapioStore()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(404, { codigo: 'campus_nao_encontrado', mensagem: 'Campus não encontrado.' }),
    )

    await cardapio.carregarRefeicao({ campus: 1 })
    expect(cardapio.campusInexistente(1)).toBe(true)

    await cardapio.carregarRefeicao({ campus: 1 }, { forcar: true })
    expect(cardapio.campusInexistente(1)).toBe(false)
  })
})
