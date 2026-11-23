import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSair } from './sair'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao } from '@/services/mock/servidor'

beforeEach(async () => {
  localStorage.clear()
  reiniciarSimulacao()
  setActivePinia(createPinia())
  await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useSair (RF03.3)', () => {
  it('servidor confirma: devolve true, sai da conta e descarta os comentários guardados', async () => {
    const limparCache = vi.spyOn(useAvaliacoesStore(), 'limparCache')
    const { sair, semConfirmacao } = useSair()

    expect(await sair()).toBe(true)
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(limparCache).toHaveBeenCalledTimes(1)
    expect(semConfirmacao.value).toBe(false)
  })

  it('401 (a sessão já tinha acabado): conta como saída confirmada', async () => {
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(401, { codigo: 'nao_autenticado' }),
    )
    const { sair, semConfirmacao } = useSair()

    expect(await sair()).toBe(true)
    expect(semConfirmacao.value).toBe(false)
  })

  it('servidor não confirma: devolve false, sai deste aparelho e marca semConfirmacao', async () => {
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const limparCache = vi.spyOn(useAvaliacoesStore(), 'limparCache')
    const { sair, semConfirmacao, saindo } = useSair()

    expect(await sair()).toBe(false)
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(limparCache).toHaveBeenCalledTimes(1)
    expect(semConfirmacao.value).toBe(true)
    expect(saindo.value).toBe(false)
  })

  it('segundo pedido enquanto o primeiro não termina: devolve null, sem outro DELETE', async () => {
    let terminar
    const del = vi
      .spyOn(apiClient, 'delete')
      .mockReturnValueOnce(new Promise((resolve) => (terminar = resolve)))
    const { sair, saindo } = useSair()

    const primeiro = sair()
    expect(saindo.value).toBe(true)
    expect(await sair()).toBeNull()
    terminar(null)

    expect(await primeiro).toBe(true)
    expect(del).toHaveBeenCalledTimes(1)
  })
})
