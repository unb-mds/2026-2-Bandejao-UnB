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

    const semana = await cardapio.carregar('darcy')

    expect(semana.dias[0].data).toBe('2026-09-28')
    expect(cardapio.semana('darcy')).toEqual(semana)
    expect(cardapio.semana('gama')).toBeNull()
    expect(cardapio.carregando).toBe(false)
    expect(cardapio.erro).toBeNull()
  })

  it('usa o cache na segunda vez, e `forcar` busca de novo', async () => {
    const cardapio = useCardapioStore()
    const espiao = vi.spyOn(apiClient, 'get')

    await cardapio.carregar('darcy')
    await cardapio.carregar('darcy')
    expect(espiao).toHaveBeenCalledTimes(1)

    await cardapio.carregar('darcy', { forcar: true })
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

  it('acha a refeição de um dia; sem ela, devolve null', async () => {
    const cardapio = useCardapioStore()
    await cardapio.carregar('darcy')

    expect(cardapio.refeicao('darcy', '2026-09-28', 'almoco')).toMatchObject({ tipo: 'almoco' })
    expect(cardapio.refeicao('darcy', '2026-10-03', 'jantar')).toBeNull() // sábado só tem almoço
    expect(cardapio.refeicao('gama', '2026-09-28', 'almoco')).toBeNull() // campus não carregado
  })
})
