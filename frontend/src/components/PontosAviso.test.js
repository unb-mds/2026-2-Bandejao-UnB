import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PontosAviso from './PontosAviso.vue'
import { useGamificacaoStore } from '@/stores/gamificacao'

let pinia

function montar() {
  return mount(PontosAviso, { global: { plugins: [pinia] }, attachTo: document.body })
}

const aviso = (wrapper) => wrapper.find('[data-teste="pontos-aviso"]')

beforeEach(() => {
  vi.useFakeTimers()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('PontosAviso (FE-10, RF24.2)', () => {
  it('sem pontos recebidos: nada aparece, mas a região de aviso existe para o leitor de tela', () => {
    const wrapper = montar()

    expect(aviso(wrapper).exists()).toBe(false)
    expect(wrapper.get('[role="status"]').attributes('aria-live')).toBe('polite')
  })

  it('total 0: o aviso não aparece', async () => {
    const wrapper = montar()

    useGamificacaoStore().registrarPontos({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })
    await wrapper.vm.$nextTick()

    expect(aviso(wrapper).exists()).toBe(false)
  })

  it('total maior que 0: mostra "+N pontos"', async () => {
    const wrapper = montar()

    useGamificacaoStore().registrarPontos({ total: 10, contribuicao: 10, avaliacaoLiberada: 0 })
    await wrapper.vm.$nextTick()

    expect(aviso(wrapper).text()).toContain('+10 pontos')
  })

  it('1 ponto fica no singular', async () => {
    const wrapper = montar()

    useGamificacaoStore().registrarPontos({ total: 1 })
    await wrapper.vm.$nextTick()

    expect(aviso(wrapper).text()).toContain('+1 ponto')
    expect(aviso(wrapper).text()).not.toContain('pontos')
  })

  it('some sozinho depois de 4 segundos', async () => {
    const wrapper = montar()
    useGamificacaoStore().registrarPontos({ total: 15 })
    await wrapper.vm.$nextTick()

    vi.advanceTimersByTime(3999)
    await wrapper.vm.$nextTick()
    expect(aviso(wrapper).exists()).toBe(true)

    vi.advanceTimersByTime(1)
    await wrapper.vm.$nextTick()
    expect(aviso(wrapper).exists()).toBe(false)
  })

  it('um aviso novo recomeça a contagem e mostra o total novo', async () => {
    const wrapper = montar()
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos({ total: 10 })
    await wrapper.vm.$nextTick()
    vi.advanceTimersByTime(3000)

    gamificacao.registrarPontos({ total: 5 })
    await wrapper.vm.$nextTick()
    vi.advanceTimersByTime(3000)
    await wrapper.vm.$nextTick()

    expect(aviso(wrapper).text()).toContain('+5 pontos')
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(aviso(wrapper).exists()).toBe(false)
  })

  it('o botão de fechar tira o aviso na hora', async () => {
    const wrapper = montar()
    useGamificacaoStore().registrarPontos({ total: 10 })
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-teste="pontos-aviso-fechar"]').trigger('click')

    expect(aviso(wrapper).exists()).toBe(false)
    expect(useGamificacaoStore().aviso).toBeNull()
  })

  it('desmontar com um aviso aberto não deixa temporizador pendente', async () => {
    const wrapper = montar()
    useGamificacaoStore().registrarPontos({ total: 10 })
    await wrapper.vm.$nextTick()

    wrapper.unmount()

    expect(vi.getTimerCount()).toBe(0)
  })
})
