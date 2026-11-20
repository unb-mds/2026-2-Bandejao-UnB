import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AvisoLocalizacao from './AvisoLocalizacao.vue'
import { usePreferenciasStore } from '@/stores/preferencias'
import {
  abrirAvisoLocalizacao,
  estadoLocalizacao,
  reiniciarAvisoLocalizacaoParaTestes,
} from '@/composables/avisoLocalizacao'

/**
 * As três situações do RF19 (FE-04): "Agora não", permitido e bloqueado,
 * mais os casos do navegador real que um stub instantâneo não pega
 * (pedido fechado sem decidir, navegador que nunca responde, aparelho sem
 * sinal, exceção, HTTP sem TLS).
 */
const erroGeo = (code) => ({ code, PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 })

// Como a pessoa responde ao pedido do navegador.
const aceitar = ({ ok, permissoes }) => {
  permissoes.estado = 'granted'
  ok({ coords: { latitude: -15.9, longitude: -48 } })
}
const recusar = ({ falha, permissoes }) => {
  permissoes.estado = 'denied'
  falha(erroGeo(1))
}
const dispensar = ({ falha }) => falha(erroGeo(1))
const semSinal = ({ falha, permissoes }) => {
  permissoes.estado = 'granted'
  falha(erroGeo(2))
}
const nuncaResponder = () => {}

let getCurrentPosition
let permissoes

/**
 * `estado` é o que a Permissions API responde (null: navegador sem a API);
 * `aoPedir` é o que a pessoa faz no pedido do navegador.
 */
function simularNavegador({ estado = 'prompt', aoPedir = aceitar } = {}) {
  permissoes = { estado }
  permissoes.query = vi.fn(async () => ({ state: permissoes.estado }))
  getCurrentPosition = vi.fn((ok, falha) => aoPedir({ ok, falha, permissoes }))
  vi.stubGlobal('navigator', {
    permissions: estado === null ? undefined : permissoes,
    geolocation: { getCurrentPosition },
  })
}

const montados = []
async function montar() {
  const wrapper = mount(AvisoLocalizacao, { attachTo: document.body })
  montados.push(wrapper)
  await flushPromises()
  return wrapper
}

/** Devolve { desfecho } (um objeto, para o await não esperar o aviso fechar). */
async function abrirPeloMenu() {
  const desfecho = abrirAvisoLocalizacao()
  await flushPromises()
  return { desfecho }
}

const aberto = (wrapper) => wrapper.find('dialog').attributes('open') !== undefined
const botao = (wrapper, texto) => wrapper.findAll('button').find((b) => b.text().includes(texto))
async function clicar(wrapper, texto) {
  await botao(wrapper, texto).trigger('click')
  await flushPromises()
}
async function apertarEsc(wrapper) {
  await wrapper.find('dialog').trigger('keydown', { key: 'Escape' })
  await flushPromises()
}

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  reiniciarAvisoLocalizacaoParaTestes()
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

afterEach(() => {
  montados.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('AvisoLocalizacao: ao abrir o app', () => {
  it('mostra o aviso do Bandejão sem acionar o navegador', async () => {
    simularNavegador()
    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(true)
    expect(wrapper.text()).toContain('as coordenadas não saem do aparelho')
    expect(botao(wrapper, 'Permitir')).toBeDefined()
    expect(botao(wrapper, 'Agora não')).toBeDefined()
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it.each([
    ['concedida', 'granted'],
    ['negada', 'denied'],
  ])('com a permissão já %s, não abre nada e registra o estado', async (esperado, estado) => {
    simularNavegador({ estado })
    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(false)
    expect(estadoLocalizacao.value).toBe(esperado)
  })

  it('sem Permissions API, abre enquanto a pessoa nunca permitiu', async () => {
    simularNavegador({ estado: null })
    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(true)
  })

  it('sem Permissions API, não abre de novo depois de a pessoa ter permitido', async () => {
    simularNavegador({ estado: null })
    usePreferenciasStore().registrarLocalizacaoPermitida()
    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(false)
  })

  it('sem Geolocation API, não abre nada sozinho', async () => {
    vi.stubGlobal('navigator', {})
    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(false)
  })

  it('fora de HTTPS, não abre nada sozinho', async () => {
    simularNavegador()
    vi.stubGlobal('isSecureContext', false)
    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(false)
  })

  it('usa o showModal do navegador quando existe (prende o foco no aviso)', async () => {
    const showModal = vi.fn(function () {
      this.setAttribute('open', '')
    })
    window.HTMLDialogElement.prototype.showModal = showModal
    try {
      simularNavegador()
      const wrapper = await montar()

      expect(showModal).toHaveBeenCalledOnce()
      expect(aberto(wrapper)).toBe(true)
    } finally {
      delete window.HTMLDialogElement.prototype.showModal
    }
  })
})

describe('AvisoLocalizacao: "Agora não"', () => {
  it('fecha o aviso, não aciona o navegador e guarda a escolha', async () => {
    simularNavegador()
    const wrapper = await montar()

    await clicar(wrapper, 'Agora não')

    expect(aberto(wrapper)).toBe(false)
    expect(getCurrentPosition).not.toHaveBeenCalled()
    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(true)
  })

  it('o aviso não reaparece na próxima abertura do app', async () => {
    simularNavegador()
    usePreferenciasStore().adiarAvisoLocalizacao()

    const wrapper = await montar()

    expect(aberto(wrapper)).toBe(false)
  })

  it('Esc no aviso vale como "Agora não"', async () => {
    simularNavegador()
    const wrapper = await montar()

    await apertarEsc(wrapper)

    expect(aberto(wrapper)).toBe(false)
    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(true)
  })

  it('"Usar minha localização" mostra o aviso de novo e devolve "adiado"', async () => {
    simularNavegador()
    usePreferenciasStore().adiarAvisoLocalizacao()
    const wrapper = await montar()

    const { desfecho } = await abrirPeloMenu()
    expect(aberto(wrapper)).toBe(true)
    await clicar(wrapper, 'Agora não')

    expect(await desfecho).toBe('adiado')
  })
})

describe('AvisoLocalizacao: permitido', () => {
  it('"Permitir" passa para o pedido do navegador e fecha quando a pessoa aceita', async () => {
    simularNavegador({ aoPedir: aceitar })
    const wrapper = await montar()
    const desfecho = abrirAvisoLocalizacao()

    await clicar(wrapper, 'Permitir')

    expect(getCurrentPosition).toHaveBeenCalledOnce()
    expect(aberto(wrapper)).toBe(false)
    // Só o desfecho, sem coordenadas (RI09).
    expect(await desfecho).toBe('concedida')
    expect(estadoLocalizacao.value).toBe('concedida')
  })

  it('sem Permissions API, guarda que a pessoa permitiu', async () => {
    simularNavegador({ estado: null, aoPedir: aceitar })
    const wrapper = await montar()

    await clicar(wrapper, 'Permitir')

    expect(usePreferenciasStore().localizacaoPermitida).toBe(true)
  })

  it('"Usar minha localização" com permissão já concedida confirma em vez de não fazer nada', async () => {
    simularNavegador({ estado: 'granted' })
    const wrapper = await montar()

    const { desfecho } = await abrirPeloMenu()

    expect(aberto(wrapper)).toBe(true)
    expect(wrapper.text()).toContain('A localização já está liberada')
    await clicar(wrapper, 'Entendi')
    expect(aberto(wrapper)).toBe(false)
    expect(await desfecho).toBe('concedida')
  })
})

describe('AvisoLocalizacao: enquanto o navegador pergunta', () => {
  it('"Agora não" continua disponível e uma resposta atrasada é ignorada', async () => {
    let responder
    simularNavegador({ aoPedir: (pedido) => (responder = () => aceitar(pedido)) })
    const wrapper = await montar()
    await clicar(wrapper, 'Permitir')

    expect(wrapper.text()).toContain('Agora é com o navegador')
    expect(botao(wrapper, 'Agora não').attributes('disabled')).toBeUndefined()
    await clicar(wrapper, 'Agora não')
    responder()
    await flushPromises()

    expect(aberto(wrapper)).toBe(false)
    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(true)
    expect(estadoLocalizacao.value).toBe('adiado')
  })

  it('Esc também sai, valendo como "Agora não"', async () => {
    simularNavegador({ aoPedir: nuncaResponder })
    const wrapper = await montar()
    await clicar(wrapper, 'Permitir')

    await apertarEsc(wrapper)

    expect(aberto(wrapper)).toBe(false)
    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(true)
  })

  it('se o navegador nunca responder, volta ao aviso depois do prazo', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    simularNavegador({ aoPedir: nuncaResponder })
    const wrapper = await montar()
    await clicar(wrapper, 'Permitir')

    await vi.advanceTimersByTimeAsync(30_000)
    await flushPromises()

    expect(aberto(wrapper)).toBe(true)
    expect(wrapper.text()).toContain('O navegador não respondeu')
    expect(botao(wrapper, 'Permitir').attributes('disabled')).toBeUndefined()
  })

  it('fechar o pedido sem decidir volta ao aviso, não ao passo a passo', async () => {
    simularNavegador({ aoPedir: dispensar })
    const wrapper = await montar()

    await clicar(wrapper, 'Permitir')

    expect(aberto(wrapper)).toBe(true)
    expect(wrapper.text()).not.toContain('O acesso à localização foi bloqueado')
    expect(wrapper.text()).toContain('O navegador não respondeu')
  })

  it('com a localização do aparelho desligada, avisa e deixa tentar de novo', async () => {
    simularNavegador({ aoPedir: semSinal })
    const wrapper = await montar()

    await clicar(wrapper, 'Permitir')

    expect(wrapper.text()).toContain('A localização do aparelho está desligada')
    await clicar(wrapper, 'Tentar de novo')
    expect(getCurrentPosition).toHaveBeenCalledTimes(2)
  })

  it('se getCurrentPosition lançar exceção, a tela não trava', async () => {
    simularNavegador({
      aoPedir: () => {
        throw new Error('quebrado')
      },
    })
    const wrapper = await montar()

    await clicar(wrapper, 'Permitir')

    expect(wrapper.text()).toContain('Este navegador não oferece localização')
    await clicar(wrapper, 'Fechar')
    expect(aberto(wrapper)).toBe(false)
  })

  it('uma nova abertura no meio do pedido não pede de novo ao navegador', async () => {
    simularNavegador({ aoPedir: nuncaResponder })
    const wrapper = await montar()
    await clicar(wrapper, 'Permitir')

    await abrirPeloMenu()

    expect(wrapper.text()).toContain('Agora é com o navegador')
    expect(botao(wrapper, 'Permitir').attributes('disabled')).toBeDefined()
    expect(getCurrentPosition).toHaveBeenCalledOnce()
  })
})

describe('AvisoLocalizacao: bloqueado', () => {
  it('se a pessoa recusa no navegador, mostra o passo a passo para liberar', async () => {
    simularNavegador({ aoPedir: recusar })
    const wrapper = await montar()

    await clicar(wrapper, 'Permitir')

    expect(wrapper.text()).toContain('O acesso à localização foi bloqueado')
    expect(wrapper.findAll('ol li')).toHaveLength(4)
    expect(botao(wrapper, 'Permitir')).toBeUndefined()
    expect(botao(wrapper, 'Já liberei')).toBeDefined()
  })

  it('"Usar minha localização" com o navegador bloqueado vai direto ao passo a passo', async () => {
    simularNavegador({ estado: 'denied' })
    const wrapper = await montar()

    await abrirPeloMenu()

    expect(wrapper.text()).toContain('O acesso à localização foi bloqueado')
    expect(botao(wrapper, 'Permitir')).toBeUndefined()
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it('"Já liberei" fecha se a permissão foi liberada', async () => {
    simularNavegador({ estado: 'denied' })
    const wrapper = await montar()
    const { desfecho } = await abrirPeloMenu()

    permissoes.estado = 'granted'
    await clicar(wrapper, 'Já liberei')

    expect(aberto(wrapper)).toBe(false)
    expect(await desfecho).toBe('concedida')
  })

  it('"Já liberei" com a permissão ainda negada avisa que continua bloqueado', async () => {
    simularNavegador({ estado: 'denied' })
    const wrapper = await montar()
    await abrirPeloMenu()

    await clicar(wrapper, 'Já liberei')

    expect(aberto(wrapper)).toBe(true)
    expect(wrapper.find('[role="status"]').text()).toContain('Ainda está bloqueado')
  })

  it('"Já liberei" com a permissão de volta em "Perguntar" pede ao navegador', async () => {
    simularNavegador({ estado: 'denied', aoPedir: aceitar })
    const wrapper = await montar()
    await abrirPeloMenu()

    permissoes.estado = 'prompt'
    await clicar(wrapper, 'Já liberei')

    expect(getCurrentPosition).toHaveBeenCalledOnce()
    expect(aberto(wrapper)).toBe(false)
  })

  it('"Fechar" e Esc fecham o passo a passo sem guardar "Agora não"', async () => {
    simularNavegador({ estado: 'denied' })
    const wrapper = await montar()

    const { desfecho } = await abrirPeloMenu()
    await clicar(wrapper, 'Fechar')
    expect(aberto(wrapper)).toBe(false)
    expect(await desfecho).toBe('negada')

    await abrirPeloMenu()
    await apertarEsc(wrapper)
    expect(aberto(wrapper)).toBe(false)
    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(false)
  })
})

describe('AvisoLocalizacao: aberto pelo menu sem localização possível', () => {
  it('sem Geolocation API, explica em vez de não fazer nada', async () => {
    vi.stubGlobal('navigator', {})
    const wrapper = await montar()

    const { desfecho } = await abrirPeloMenu()

    expect(wrapper.text()).toContain('Este navegador não oferece localização')
    await clicar(wrapper, 'Fechar')
    expect(await desfecho).toBe('indisponivel')
  })

  it('fora de HTTPS, explica que precisa de conexão segura', async () => {
    simularNavegador({ estado: 'denied' })
    vi.stubGlobal('isSecureContext', false)
    const wrapper = await montar()

    await abrirPeloMenu()

    expect(wrapper.text()).toContain('conexão segura')
    expect(wrapper.text()).not.toContain('O acesso à localização foi bloqueado')
  })

  it('ao fechar, o foco volta para quem abriu o aviso', async () => {
    simularNavegador({ estado: 'denied' })
    const wrapper = await montar()
    const origem = document.createElement('button')
    document.body.appendChild(origem)
    origem.focus()

    await abrirPeloMenu()
    await clicar(wrapper, 'Fechar')

    expect(document.activeElement).toBe(origem)
  })
})
