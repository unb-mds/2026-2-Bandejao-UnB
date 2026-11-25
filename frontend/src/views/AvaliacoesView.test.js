import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import AvaliacoesView from './AvaliacoesView.vue'

/**
 * Tela de Avaliações (revisão do PR #223): qual refeição ela abre e se o
 * widget recomeça ao trocar de refeição.
 */
const SEGUNDA = (hora, minuto = 0) => new Date(2026, 8, 28, hora, minuto)
const HOJE = '2026-09-28'
const AMANHA = '2026-09-29'

let pinia
const montados = []

async function montar({ campus = 1, data = null, refeicao = null } = {}) {
  const preferencias = usePreferenciasStore()
  preferencias.escolherCampus(campus)
  preferencias.selecionar(data, refeicao)
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push('/avaliacoes')
  await router.isReady()
  const wrapper = mount(AvaliacoesView, {
    global: { plugins: [pinia, router] },
    attachTo: document.body,
  })
  montados.push(wrapper)
  await flushPromises()
  return wrapper
}

const subtitulo = (wrapper) => wrapper.get('.subtitulo').text()

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA(12))
  localStorage.clear()
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  montados.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('AvaliacoesView — refeição que a tela abre', () => {
  it('sem seleção: a refeição de hoje em andamento', async () => {
    const wrapper = await montar()

    expect(subtitulo(wrapper)).toContain('Almoço')
    expect(subtitulo(wrapper)).toContain('28/09')
  })

  it('seleção completa vinda do cardápio é respeitada', async () => {
    const wrapper = await montar({ data: AMANHA, refeicao: 'jantar' })

    expect(subtitulo(wrapper)).toContain('Jantar')
    expect(subtitulo(wrapper)).toContain('29/09')
  })

  it('seleção só com o dia: fica no dia escolhido, na primeira refeição servida', async () => {
    const wrapper = await montar({ data: AMANHA })

    expect(subtitulo(wrapper)).toContain('29/09')
    expect(subtitulo(wrapper)).toContain('Café da Manhã')
  })

  it('ignora a refeição que o campus não serve (Planaltina não tem jantar)', async () => {
    vi.setSystemTime(SEGUNDA(16))
    const wrapper = await montar({ campus: 4 })

    expect(subtitulo(wrapper)).toContain('Almoço')
  })

  it('refeição selecionada que o campus não serve: cai na que ele serve', async () => {
    vi.setSystemTime(SEGUNDA(18))
    const wrapper = await montar({ campus: 4, data: HOJE, refeicao: 'jantar' })

    expect(subtitulo(wrapper)).toContain('Almoço')
  })

  it('trocar a refeição recomeça o widget (sem rascunho da anterior)', async () => {
    const wrapper = await montar({ data: HOJE, refeicao: 'almoco' })
    const widget = wrapper.findComponent({ name: 'AvaliacaoWidget' })

    usePreferenciasStore().selecionar(HOJE, 'cafe')
    await flushPromises()

    const novo = wrapper.findComponent({ name: 'AvaliacaoWidget' })
    expect(novo.exists()).toBe(true)
    expect(novo.vm).not.toBe(widget.vm)
    expect(subtitulo(wrapper)).toContain('Café da Manhã')
  })
})
