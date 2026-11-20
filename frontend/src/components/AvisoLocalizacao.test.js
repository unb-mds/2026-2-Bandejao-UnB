import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AvisoLocalizacao from './AvisoLocalizacao.vue'
import { usePreferenciasStore } from '@/stores/preferencias'
import { abrirAvisoLocalizacao, fecharAvisoLocalizacao } from '@/composables/avisoLocalizacao'

/**
 * As três situações do RF19 (FE-04): "Agora não", permitido e bloqueado.
 * O navegador é simulado: `estado` é o que a Permissions API responde e
 * `respostaDoPedido` é o que a pessoa faz no pedido do navegador.
 */
let getCurrentPosition
function simularNavegador({ estado = 'prompt', respostaDoPedido = 'permitir' } = {}) {
  getCurrentPosition = vi.fn((sucesso, falha) => {
    if (respostaDoPedido === 'permitir') sucesso({ coords: { latitude: -15.9, longitude: -48 } })
    else falha({ code: 1, PERMISSION_DENIED: 1 })
  })
  vi.stubGlobal('navigator', {
    permissions: { query: vi.fn(async () => ({ state: estado })) },
    geolocation: { getCurrentPosition },
  })
}

async function montar() {
  const wrapper = mount(AvisoLocalizacao, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

const botao = (wrapper, texto) => wrapper.findAll('button').find((b) => b.text().includes(texto))

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  fecharAvisoLocalizacao()
})

afterEach(() => {
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

describe('AvisoLocalizacao', () => {
  it('no primeiro acesso mostra o aviso do Bandejão sem acionar o navegador', async () => {
    simularNavegador()
    const wrapper = await montar()

    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('as coordenadas não saem do aparelho')
    expect(botao(wrapper, 'Permitir')).toBeDefined()
    expect(botao(wrapper, 'Agora não')).toBeDefined()
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  describe('"Agora não"', () => {
    it('fecha o aviso, não aciona o navegador e guarda a escolha', async () => {
      simularNavegador()
      const wrapper = await montar()

      await botao(wrapper, 'Agora não').trigger('click')

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
      expect(getCurrentPosition).not.toHaveBeenCalled()
      expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(true)
    })

    it('o aviso não reaparece na próxima abertura do app', async () => {
      simularNavegador()
      usePreferenciasStore().adiarAvisoLocalizacao()

      const wrapper = await montar()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    })

    it('"Usar minha localização" mostra o aviso de novo mesmo depois do "Agora não"', async () => {
      simularNavegador()
      usePreferenciasStore().adiarAvisoLocalizacao()
      const wrapper = await montar()

      abrirAvisoLocalizacao()
      await flushPromises()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
      expect(botao(wrapper, 'Permitir')).toBeDefined()
    })
  })

  describe('permitido', () => {
    it('"Permitir" passa para o pedido do navegador e fecha quando a pessoa aceita', async () => {
      simularNavegador({ respostaDoPedido: 'permitir' })
      const wrapper = await montar()

      await botao(wrapper, 'Permitir').trigger('click')
      await flushPromises()

      expect(getCurrentPosition).toHaveBeenCalledOnce()
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
      expect(wrapper.emitted('permitido')).toHaveLength(1)
    })

    it('com a permissão já concedida, não mostra o aviso e segue para a detecção', async () => {
      simularNavegador({ estado: 'granted' })
      const wrapper = await montar()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
      expect(getCurrentPosition).not.toHaveBeenCalled()
      expect(wrapper.emitted('permitido')).toHaveLength(1)
    })

    it('"Usar minha localização" com permissão já concedida não mostra o aviso', async () => {
      simularNavegador({ estado: 'granted' })
      const wrapper = await montar()

      abrirAvisoLocalizacao()
      await flushPromises()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
      // Um ao abrir o app e outro ao tocar em "Usar minha localização".
      expect(wrapper.emitted('permitido')).toHaveLength(2)
    })
  })

  describe('bloqueado', () => {
    it('se a pessoa recusa no navegador, mostra o passo a passo para liberar', async () => {
      simularNavegador({ respostaDoPedido: 'recusar' })
      const wrapper = await montar()

      await botao(wrapper, 'Permitir').trigger('click')
      await flushPromises()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('O acesso à localização foi bloqueado')
      expect(wrapper.findAll('ol li').length).toBeGreaterThan(0)
    })

    it('com o navegador já bloqueado, não abre nada sozinho ao abrir o app', async () => {
      simularNavegador({ estado: 'denied' })
      const wrapper = await montar()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    })

    it('"Usar minha localização" com o navegador bloqueado vai direto ao passo a passo', async () => {
      simularNavegador({ estado: 'denied' })
      const wrapper = await montar()

      abrirAvisoLocalizacao()
      await flushPromises()

      expect(wrapper.text()).toContain('O acesso à localização foi bloqueado')
      expect(botao(wrapper, 'Permitir')).toBeUndefined()
      expect(getCurrentPosition).not.toHaveBeenCalled()
    })

    it('"Já liberei" confere de novo e fecha se a permissão foi liberada', async () => {
      simularNavegador({ estado: 'denied' })
      const wrapper = await montar()
      abrirAvisoLocalizacao()
      await flushPromises()

      simularNavegador({ estado: 'granted' })
      await botao(wrapper, 'Já liberei').trigger('click')
      await flushPromises()

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
      expect(wrapper.emitted('permitido')).toHaveLength(1)
    })

    it('"Fechar" no passo a passo fecha o aviso', async () => {
      simularNavegador({ estado: 'denied' })
      const wrapper = await montar()
      abrirAvisoLocalizacao()
      await flushPromises()

      await botao(wrapper, 'Fechar').trigger('click')

      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    })
  })
})
