import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAvaliacoesStore } from './avaliacoes'
import { useAuthStore } from './auth'
import { apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao } from '@/services/mock/servidor'

/** avaliacoesStore com o servidor simulado (Plano de Testes 3.1; módulo crítico). */

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)
const ALMOCO_HOJE = { campus: 3, data: '2026-09-28', refeicao: 'almoco' }

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
})

describe('avaliacoesStore', () => {
  it('carrega as avaliações de uma refeição e guarda pela refeição', async () => {
    const avaliacoes = useAvaliacoesStore()

    const daRefeicao = await avaliacoes.carregar(ALMOCO_HOJE)

    expect(daRefeicao.quantidade).toEqual(expect.any(Number))
    expect(avaliacoes.daRefeicao(ALMOCO_HOJE)).toBe(daRefeicao)
    expect(avaliacoes.daRefeicao({ ...ALMOCO_HOJE, refeicao: 'jantar' })).toBeNull()
  })

  it('carrega o resumo da semana do campus', async () => {
    const avaliacoes = useAvaliacoesStore()

    const resumo = await avaliacoes.carregarResumo(3)

    expect(resumo).not.toBeNull()
    expect(avaliacoes.resumoPorCampus[3]).toBe(resumo)
  })

  it('erro ao carregar fica em `erro` e devolve o que já havia', async () => {
    const avaliacoes = useAvaliacoesStore()

    expect(await avaliacoes.carregar({ campus: 3 })).toBeNull()
    expect(avaliacoes.erro).toBe('Informe campus, data e refeição.')

    expect(await avaliacoes.carregarResumo('executivo')).toBeNull()
    expect(avaliacoes.erro).toBe('Campus não encontrado.')
  })

  it('enviar grava a nota e atualiza a refeição e o resumo', async () => {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    const avaliacoes = useAvaliacoesStore()

    const resposta = await avaliacoes.enviar(ALMOCO_HOJE, 4, 'Bom')

    expect(resposta).toMatchObject({ nota: 4, comentario: 'Bom' })
    expect(avaliacoes.daRefeicao(ALMOCO_HOJE).minha).toEqual({ nota: 4, comentario: 'Bom' })
    expect(avaliacoes.resumoPorCampus[3]).not.toBeUndefined()
  })

  it('enviar sem login rejeita com o erro da API', async () => {
    const avaliacoes = useAvaliacoesStore()

    const falha = await avaliacoes.enviar(ALMOCO_HOJE, 4, '').catch((e) => e)

    expect(falha.codigo).toBe('nao_autenticado')
  })

  it('limparCache esquece as avaliações carregadas (login e logout)', async () => {
    const avaliacoes = useAvaliacoesStore()
    await avaliacoes.carregar(ALMOCO_HOJE)

    avaliacoes.limparCache()

    expect(avaliacoes.daRefeicao(ALMOCO_HOJE)).toBeNull()
  })
})

describe('avaliacoesStore: resumo do dia (GET /api/avaliacoes/resumo/)', () => {
  it('carrega as notas de todas as refeições do dia numa chamada só', async () => {
    const avaliacoes = useAvaliacoesStore()
    const get = vi.spyOn(apiClient, 'get')

    const resumo = await avaliacoes.carregarResumoDoDia(1, '2026-09-28')

    expect(get).toHaveBeenCalledWith('/avaliacoes/resumo/?campus=1&data=2026-09-28')
    expect(resumo.map((r) => r.tipo)).toEqual(['cafe', 'almoco', 'jantar'])
    expect(avaliacoes.daResumoDoDia(1, '2026-09-28')).toEqual(resumo)
    expect(avaliacoes.daResumoDoDia(1, '2026-09-29')).toBeNull()
  })
})
